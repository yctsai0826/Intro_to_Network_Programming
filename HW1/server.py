import socket


def startUCPserver():
    UDPport = input("Please enter your UDP port to start up (11005/11006): ")
    
    # create UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(('', int(UDPport)))
    print(f"Server has started on {UDPport}, waiting for game invitation...")
    
    invitation_accepted = False
    player_a_ip = None
    player_a_tcp_port = None
    
    while True:
        # waiting for checking or invitation message
        data, addr = udp_socket.recvfrom(1024)
        message = data.decode()
        
        if message == "Is available?":
            udp_socket.sendto("Player available".encode(), addr)
            
        elif message.startswith("Invitation from"):
            print(f"{addr[0]}: connected")
            player_name = message[len("Invitation from "):]
            print(f"Received invitation from {player_name}")
            
            accept = input("Do you accept the invitation? (yes/no): ").strip().lower()
            if accept == 'yes':
                udp_socket.sendto("Invitation accepted".encode(), addr)
                invitation_accepted = True
                player_a_ip = addr[0]
            else:
                udp_socket.sendto("Invitation declined".encode(), addr)
                
        elif invitation_accepted and player_a_tcp_port is None:
            try:
                player_a_tcp_port = int(message)
                print(f"Received TCP port {player_a_ip}: {player_a_tcp_port} from Player A")
                
                # exit the loop and close the UDP server
                udp_socket.close()
                return player_a_ip, player_a_tcp_port
            except ValueError:
                print(f"Unexpected message: {message}")
                
        else:
            print(f"Unexpected message: {message}")
            
            
def connectTCP(player_a_ip, player_a_tcp_port):
    # Connect to Player A's TCP server
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((player_a_ip, player_a_tcp_port))
        print(f"Connected to Player A's TCP server at {player_a_ip}:{player_a_tcp_port}")
        
        # Start paper scissors rock game
        while True:
            # Send your move to Player A
            move = input("Enter your move (rock/paper/scissors): ").strip().lower()
            if (move == "exit"):
                print("Exiting the game...")
                break
            tcp_socket.send(move.encode())
            
            # Receive Player A's move
            print("Waiting for Player A's move...")
            player_a_move = tcp_socket.recv(1024).decode()
            
            print(f"Player A chose: {player_a_move}")
            print(f"You chose: {move}")
            
            # Determine the winner
            if move == player_a_move:
                result = "It's a tie!\n"
            elif (move == 'rock' and player_a_move == 'scissors') or \
                (move == 'paper' and player_a_move == 'rock') or \
                (move == 'scissors' and player_a_move == 'paper'):
                result = "You win!\n"
            else:
                result = "You lose!\n"
            
            print(result)
        
        # Close the TCP connection
        tcp_socket.close()
    except socket.error as err:
        print(f"Failed to connect to Player A's TCP server: {err}")
                
            
    

def main():
    TCPIP, TCPport = startUCPserver()
    connectTCP(TCPIP, TCPport)
    

if __name__ == "__main__":
    main()
