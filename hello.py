def main():
    print("Hello from state-mind-machine!")


if __name__ == "__main__":
    main()
    from sence.vlan import VLANServer
    VLANServer("127.0.0.1", 5000).start()
