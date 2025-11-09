from pyngrok import ngrok

public_url = ngrok.connect(8000)  # or your port number
print(public_url)
