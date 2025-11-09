from pyngrok import ngrok

public_url = ngrok.connect("http://199.247.26.114:8000")  # or your port number
print(public_url)
