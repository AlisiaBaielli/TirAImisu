"""Utilities to extract medication information from an image using a multimodal model.

Primary entry: extract_medication_data_from_image(image, api_key=None, ...)

Behavior:
- The function sends a small base64 prefix of the image to a GPT-5-like multimodal model
	and instructs it to return a JSON object with the fields medication_name, dosage, and
	num_pills. If any field cannot be determined from the image, the model should return null
	for that field.

The function returns a dict with keys: medication_name, dosage, num_pills.
The user must provide an API key (or set OPENAI_API_KEY in the environment) before calling.
"""

from __future__ import annotations

from typing import Optional, Union, Dict, Any
import os
import json
import re
import base64

from pydantic import BaseModel, field_validator
import openai
import time

try:
	import cv2
	_HAS_OPENCV = True
except Exception:
	cv2 = None  # type: ignore
	_HAS_OPENCV = False


class MedicationData(BaseModel):
	medication_name: Optional[str] = None
	dosage: Optional[str] = None
	num_pills: Optional[int] = None

	@field_validator("medication_name", mode="before")
	@classmethod
	def clean_name(cls, v):
		if v is None:
			return None
		v = str(v).strip()
		return v or None

	@field_validator("dosage", mode="before")
	@classmethod
	def clean_dosage(cls, v):
		if v is None:
			return None
		v = str(v).strip()
		return v or None

	@field_validator("num_pills", mode="before")
	@classmethod
	def parse_num_pills(cls, v):
		if v is None:
			return None
		# If already an int
		if isinstance(v, int):
			return v
		s = str(v)
		# find a number in the string
		m = re.search(r"(\d+)", s)
		if m:
			try:
				return int(m.group(1))
			except Exception:
				return None
		return None


def _clean_model_response_to_json(text: str) -> Dict[str, Any]:
	"""Try to find the first JSON object in the model text and return parsed JSON."""
	# Look for JSON object in text
	idx = text.find("{")
	if idx == -1:
		# nothing that looks like JSON; try to wrap lines as key: value
		raise ValueError("No JSON object found in model response")
	jtxt = text[idx:]
	stack = []
	end = None
	for i, ch in enumerate(jtxt):
		if ch == '{':
			stack.append('{')
		elif ch == '}':
			if stack:
				stack.pop()
				if not stack:
					end = i + 1
					break
	if end is None:
		raise ValueError("Could not find balanced JSON object in model response")
	jsubstr = jtxt[:end]
	try:
		return json.loads(jsubstr)
	except Exception:
		cleaned = jsubstr.strip().strip('`')
		return json.loads(cleaned)


def extract_medication_data_from_image(image: Union[bytes, str]) -> Dict[str, Any]:
	"""Extract medication_name, dosage, and num_pills from an image using a multimodal model.

	Parameters
	- image: bytes or a file path (str) to the image captured from webcam
	- api_key: API key for OpenAI-like service. If None, reads from OPENAI_API_KEY env var.
	- model: model name to call (default: "gpt-5").
	- openai_api_base: optional base URL if using an alternate OpenAI-compatible API.

	Returns a dict: {"medication_name": str|None, "dosage": str|None, "num_pills": int|None}
	"""

	key = os.getenv("OPENAI_API_KEY")
	if not key:
		raise RuntimeError("No API key provided and no client passed. Set OPENAI_API_KEY env var.")

	model = "gpt-5"
	client = openai.OpenAI(api_key=key, base_url=os.getenv("OPENAI_BASE_URL"))

	if isinstance(image, str):
		with open(image, "rb") as f:
			image_bytes = f.read()
	else:
		image_bytes = image

	# Build prompt: instruct the model to analyze the attached image. Do NOT rely on
	# any base64 prefix embedded in the prompt — the image will be supplied separately
	# to the multimodal endpoint. The model should return only JSON.
	prompt = (
		"You are a visual assistant. Analyze the attached image of a medication bottle, "
		"blister pack, or pill container and extract structured medication information. "
		"Return ONLY a single JSON object with keys: medication_name, dosage, num_pills. "
		"If any field is not visible or cannot be determined from the image, set its value to null.\n\n"
		"When answering, consider visible printed label text (brand/generic), numeric strengths (e.g., 50 mg), "
		"and visible pill count (e.g., number of pills in a blister or the qty printed on the label). "
		"Respond ONLY with JSON. Example: {\"medication_name\": \"Sertraline\", "
		"\"dosage\": \"50 mg\", \"num_pills\": 28}"
	)

	# Prepare the full data URL for the image (OpenAI vision models accept data URLs)
	data_url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")

	messages = [
		{
			"role": "user",
			"content": [
				{"type": "text", "text": prompt},
				{"type": "image_url", "image_url": {"url": data_url}},
			],
		}
	]

	resp = client.chat.completions.create(model=model, messages=messages, temperature=1)

	model_text = resp.choices[0].message.content.strip()

	parsed = None
	try:
		parsed = _clean_model_response_to_json(model_text)
	except Exception:
		# As a fallback, ask the model again to output strict JSON (one retry)
		retry_prompt = (
			"Please respond ONLY with a single JSON object with the keys: medication_name, dosage, num_pills. "
			"Do not include any additional text. If unknown, set value to null.\n\nOriginal response:\n" + model_text
		)

		retry_messages = [
			{
				"role": "user",
				"content": [
					{"type": "text", "text": retry_prompt},
					{"type": "image_url", "image_url": {"url": data_url}},
				],
			}
		]

		resp2 = client.chat.completions.create(model=model, messages=retry_messages, temperature=1)
		model_text2 = resp2.choices[0].message.content.strip()
		parsed = _clean_model_response_to_json(model_text2)

	med = MedicationData(**parsed)
	return med.dict()


# def capture_image_from_webcam(device: int = 0, width: int = 1280, height: int = 720, timeout: int = 60) -> bytes:
# 	"""Open the webcam and capture a single image, returning JPEG bytes.

# 	Controls:
# 	- Press SPACE or 's' to capture the current frame.
# 	- Press 'q' or ESC to cancel and raise RuntimeError.

# 	Parameters:
# 	- device: camera device index (default 0).
# 	- width, height: requested capture resolution.
# 	- timeout: maximum seconds to wait for a capture before raising TimeoutError.

# 	Returns:
# 	- JPEG bytes suitable for passing to extract_medication_data_from_image.
# 	"""

# 	if not _HAS_OPENCV:
# 		raise RuntimeError("OpenCV (opencv-python) is required for webcam capture. Install with: pip install opencv-python")

# 	cap = cv2.VideoCapture(device, cv2.CAP_DSHOW if os.name == 'nt' else 0)
# 	if not cap.isOpened():
# 		raise RuntimeError(f"Could not open webcam device {device}")

# 	cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
# 	cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

# 	window_name = "Capture - press SPACE to take photo, Q to quit"
# 	cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
# 	start = time.time()
# 	captured_bytes = None

# 	try:
# 		while True:
# 			ret, frame = cap.read()
# 			if not ret:
# 				time.sleep(0.1)
# 				if time.time() - start > timeout:
# 					raise TimeoutError("Timed out waiting for webcam frames")
# 				continue

# 			cv2.imshow(window_name, frame)

# 			key = cv2.waitKey(1) & 0xFF
# 			# SPACE or 's' to capture
# 			if key == 32 or key == ord('s'):
# 				success, encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
# 				if not success:
# 					raise RuntimeError("Failed to encode captured frame to JPEG")
# 				captured_bytes = encoded.tobytes()
# 				break
# 			if key == ord('q') or key == 27:
# 				raise RuntimeError("User cancelled webcam capture")

# 			if time.time() - start > timeout:
# 				raise TimeoutError("Timed out waiting for user to capture image")
# 	finally:
# 		try:
# 			cap.release()
# 		except Exception:
# 			pass
# 		try:
# 			cv2.destroyWindow(window_name)
# 		except Exception:
# 			pass

# 	if captured_bytes is None:
# 		raise RuntimeError("No image captured from webcam")

# 	return captured_bytes
