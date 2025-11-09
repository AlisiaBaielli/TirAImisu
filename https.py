from pyngrok import ngrok

# Use your VM's public IP (works because curl worked)
vm_ip = "199.247.26.114"
public_url = ngrok.connect(f"http://{vm_ip}")
print("Public HTTPS URL:", public_url)

# Keep this script running while demoing
