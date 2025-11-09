from pyngrok import ngrok
import socket


def get_vm_ip():
    """
    Automatically detect the VM's public IP.
    Falls back to hostname resolution if needed.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # connect to a public DNS to find outgoing IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    vm_ip = get_vm_ip()
    frontend_port = 80  # Your web frontend port

    print(f"Detected VM IP: {vm_ip}")
    print(f"Starting ngrok tunnel to http://{vm_ip}:{frontend_port} ...")

    # Create HTTPS tunnel
    public_url = ngrok.connect(frontend_port, bind_tls=True)
    print("\n🚀 Your public HTTPS URL for the frontend:")
    print(public_url)

    print("\nKeep this script running while demoing. Ctrl+C to exit.")
    input("Press Enter to exit and close ngrok tunnel...\n")
