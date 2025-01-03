import socket

MIN_PORT = 10000  # UDP伺服器的最小埠號
MAX_PORT = 65535  # 最大埠號
SERVER_HOSTS = [
    "140.113.235.151",
    "140.113.235.152",
    "140.113.235.153",
    "140.113.235.154"
]

PORTS = [
    11005, 11006
]

def checkserver(server_ip, port):
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as err:
        print(f"Socket creation failed: {err}")
        return False

    server_addr = (server_ip, port)
    ping_msg = "Is available?"
    
    try:
        # 1-1. send "available" message to the UDP server
        sock.sendto(ping_msg.encode(), server_addr)
        
        # 1-2. wait for the server response
        sock.settimeout(5)  # timeout for response
        buffer, _ = sock.recvfrom(1024)
    except socket.error:
        sock.close()
        return False

    # 1-3. check if the server is available
    if buffer.decode() == "Player available":
        print(f"Server IP: {server_ip}, Port: {port}")
        sock.close()
        return True
    
    sock.close()
    return False


def sendInvitation(server_ip, port, player_name):
    print("Waiting response...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as err:
        print(f"Socket creation failed: {err}")
        return False, None

    server_addr = (server_ip, port)
    invite_msg = f"Invitation from {player_name}"

    try:
        # 2-2-1. send invitation
        sock.sendto(invite_msg.encode(), server_addr)
        
        # 2-2-2. wait for the response from playerB
        buffer, _ = sock.recvfrom(1024)
        buffer = buffer.decode()
    except socket.error as err:
        print(f"Send invitation failed: {err}")
        sock.close()
        return False, None

    # 2-2-3. check if the playerB accepted the invitation, if yes then send the TCP port
    if buffer == "Invitation accepted":
        print("Connection success")
        TCPport = int(input("Please enter your TCP port: "))
        invite_msg = f"{TCPport}"
        sock.sendto(invite_msg.encode(), server_addr)
        sock.close()
        return True, TCPport
    
    sock.close()
    return False, None


def startTCPserver(TCPport):
    # 3-2. Start the TCP server on the specified port
    try:
        # Create a TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('', TCPport))
        
        # Set the socket to listen for incoming connections
        server_socket.listen(1)
        print(f"TCP server started on port {TCPport}. Waiting for player B to connect...")

        # Accept a connection from player B
        conn, addr = server_socket.accept()
        print(f"Player B connected from {addr}")
        
        # Start paper scissors rock game
        while True:
            # Receive Player B's move
            print("Waiting for Player B's move...")
            player_b_move = conn.recv(1024).decode()

            # Prompt Player A to enter their move
            move = input("Enter your move (rock/paper/scissors): ").strip().lower()
            if (move == "exit"):
                print("Exiting the game...")
                break
            conn.send(move.encode())

            print(f"Player B chose: {player_b_move}")
            print(f"You chose: {move}")
            
            # Determine the winner
            if move == player_b_move:
                result = "It's a tie!"
            elif (move == 'rock' and player_b_move == 'scissors') or \
                (move == 'paper' and player_b_move == 'rock') or \
                (move == 'scissors' and player_b_move == 'paper'):
                result = "You win!"
            else:
                result = "You lose!"

            print(result)

        # Close the connection
        conn.close()
    except socket.error as err:
        print(f"Failed to start TCP server: {err}")



def main():
    player_name = input("Please enter your name: ")
    
    found = False
    print("Searching for waiting players...")
    for server_ip in SERVER_HOSTS:
        for port in PORTS:
            if checkserver(server_ip, port):
                found = True
    
    if not found:
        print("No available player found")
        return

    # 2-1. choose a player to send invitation
    print("Please enter the player IP and port you want to invite:")

    chosen_ip = input("Player IP: ")
    chosen_port = int(input("Player Port: "))
    
    # 2-2. send invitation and wait until playerB accept the invitation
    accept, TCPport = sendInvitation(chosen_ip, chosen_port, player_name)
    while not accept:
        print("Invitation failed, please try again")
        accept, TCPport = sendInvitation(chosen_ip, chosen_port, player_name)
    
    # 3-1. send the TCP port to the server
    startTCPserver(TCPport)
    


if __name__ == "__main__":
    main()
