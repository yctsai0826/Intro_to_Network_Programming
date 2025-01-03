import socket
import threading
import time

SERVER_HOSTS = [
    "140.113.235.151",
    "140.113.235.152",
    "140.113.235.153",
    "140.113.235.154"
]

class LobbyServer:
    def __init__(self, host='127.0.0.1', port=11005):
        while True:
            try:
                self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server.bind((host, port))
                self.server.listen(5)
                print(f"Lobby Server started on {host}:{port}")
                break  # 成功啟動後離開循環
            except socket.error as e:
                print(f"Error starting server on port {port}: {e}")
                port += 1
                print(f"Retrying with port {port}...")
            
        self.clients = {}  # {username: (conn, addr, password)}
        self.players = {}  # {username: [conn, addr, status]}
        self.rooms = {}  # {room_name: [[client1, client2], game_type, status, private/public, Gameport]}
        self.lock = 0


    def handle_client(self, conn, addr):
        print(f"New connection from {addr}")
        username = None
        try:
            while True:
                while self.lock:
                    pass
                msg = conn.recv(1024).decode()
                print(f"{msg=}")
                if not msg:
                    break
                if msg.startswith("REGISTER"):
                    username, password = msg.split()[1:3]
                    while (self.register(username, password, conn, addr) == False):
                        msg = conn.recv(1024).decode()
                        username, password = msg.split()[1:3]
                    
                elif msg.startswith("LOGIN"):
                    username = msg.split()[1]
                    self.login(username, conn, addr)
                        
                elif msg.startswith("CREATE_ROOM"):
                    self.create_room(conn, addr)
                        
                elif msg.startswith("JOIN_ROOM"):
                    self.join_room(conn, addr)
                    room_name = msg.split()[1]
                    if room_name in self.rooms:
                        self.rooms[room_name].append(username)
                        conn.sendall(f"Joined room {room_name}".encode())
                    else:
                        conn.sendall("ERROR Room not found".encode())
                        
                elif msg.startswith("LOGOUT"):
                    username = msg.split()[1]
                    print("logging out...")
                    del self.players[username]
                    conn.sendall("SUCCESS Logged out".encode())
                
                elif msg == "LIST_ROOMS":
                    self.list_rooms(conn, addr)
                
                elif msg.startswith("EXIT"):
                    user = msg.split()[1]
                    del self.clients[user]
                    
                elif msg == "NOTHING":
                    self.run_nothing(conn, addr)
                    
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            conn.close()


    def start(self):
        print("Lobby Server is running...")
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
                       
    def register(self, username, password, conn, addr):
        if username in self.clients:
            conn.sendall("ERROR Username already exists".encode())
            return False
        # Username available
        self.clients[username] = [conn, addr, password]     # 0 = waiting, 1 = playing, 2: In room
        conn.sendall("SUCCESS Registered".encode())
        return True
       
    def login(self, username, conn, addr):
        while True:
            if username in self.clients:
                conn.sendall("User exist.".encode())
                break
            elif username not in self.clients:
                conn.sendall("ERROR User does not exist".encode())
            # elif username in self.players:
            #     conn.sendall("ERROR User is already logged in".encode())
            msg = conn.recv(1024).decode()
            username = msg.split()[1]
        while True:
            password = conn.recv(1024).decode()
            if password == self.clients[username][2]:
                conn.sendall("SUCCESS Logged in".encode())
                self.players[username] = [conn, addr, 0]
                return
            conn.sendall("ERROR Incorrect password".encode())
            
    def create_room(self, conn, addr):
        while True:
            response = conn.recv(1024).decode()
            room_name, host_name = response.split()
            if room_name in self.rooms:
                conn.sendall("ERROR Room already exists".encode())
            else:
                # self.rooms[room_name] = [[host_name, None], 0, 0, "public"]
                conn.sendall(f"Room {room_name} created".encode())
                break
            
        response = conn.recv(1024).decode()
        game_type, public = response.split()
        self.rooms[room_name] = [[host_name, None], game_type, "0", public, None]
        conn.sendall(f"SUCCESS Room created".encode())
        self.players[host_name][2] = 2  # In room
        
        if public == "1":
            return
        
        # Private room
        self.list_idle_players(conn, addr)
        
        while True:
            comm = conn.recv(1024).decode()
            print(f"{comm=}")
            if comm == "LIST_IDLE_PLAYERS":
                self.list_idle_players(conn, addr)
            else:
                client_name = comm
                client_conn = self.players[client_name][0]
                if client_name in self.players and self.players[client_name][2] == 0:   # waiting
                    conn.sendall(f"Invited {client_name}".encode())
                    client_conn.sendall(f"Invited to {room_name}".encode())
                    print("Waiting for accept/reject response...")
                    response = client_conn.recv(1024).decode() # wait for player B's response
                    self.lock = 0
                    print(f"{response=}")
                    if response == "ACCEPT":
                        self.players[client_name][2] = 2
                        self.rooms[room_name][0][1] = client_name
                        conn.sendall(f"ACCEPTED".encode())
                        break
                conn.sendall("ERROR User not found or rejected".encode())
                
        # Request for IP and PORT
        client_conn  = self.players[client_name][0]
        time.sleep(0.5)
        conn.sendall(f"Request for IP and PORT".encode())
        response = conn.recv(1024).decode()
        print(f"2.{response=}")
        hostIP, hostPort = response.split()
        # Room: waiting to playing, fill player 2, fill Gameport(optional)
        self.rooms[room_name][4] = hostPort
        client_conn.sendall(f"{hostIP} {hostPort} {self.rooms[room_name][1]}".encode())
        
        # Wait for notification of game start
        print("\nWaiting for game start...")
        response = conn.recv(1024).decode()
        print(f"start:{response=}")
        if response == "START":
            print("Game start...\n")
            self.players[client_name][2] = 1
            self.players[self.rooms[room_name][0][0]][2] = 1
            self.rooms[room_name][2] = 1
            
        # Wait for notification of game end
        print("\nWaiting for game end...")
        response = conn.recv(1024).decode()
        print(f"end:{response=}")
        if response == "END":
            print("Game ended...\n")
            self.players[client_name][2] = 0 # status = waiting
            self.players[self.rooms[room_name][0][0]][2] = 0    # status = waiting
            del self.rooms[room_name]   # Delete the room
        
        
    def list_idle_players(self, conn, addr):
        print("Listing idle players...")
        response = "\n"
        if self.players:
            player_list = "\n".join([
                f"    Username: [{username}]"
                for username, (conn, addr, status) in self.players.items() if status == 0
            ])
            if player_list == "":
                response += "Idle players:\nNo other online player available.\n\n"
            else:
                response += f"Idle players:\n{player_list}\n\n"
        conn.sendall(response.encode())
        
    def list_rooms(self, conn, addr):
        response = ""

        if self.players:
            player_list = "\n".join([
                f"    [{username}] status: {'waiting' if status == 0 else 'playing' if status == 1 else 'In room'}"
                for username, (conn, addr, status) in self.players.items()
            ])
            response += f"Online players:\n{player_list}\n\n"
        else:
            response += "Online players:\nNo other online player available.\n\n"

        if self.rooms:
            room_list = "".join([
                f"\n    [{room}]: {'game1' if game == '1' else 'game2'}\n      -host: {users[0]}, client: {users[1]}      -status: {'waiting' if status == '0' else 'playing'}...\n"
                for room, (users, game, status, public, GamePort) in self.rooms.items()
                if public != "0"
            ])
            response += f"Available rooms:\n{room_list}"
        else:
            response += "Available rooms:\n    No rooms available."

        conn.sendall(response.encode())

    def join_room(self, conn, addr):
        while True:
            room_name = conn.recv(1024).decode().strip()
            if room_name in self.rooms and (self.rooms[room_name][3] == "1") and self.rooms[room_name][2] == "0" and self.rooms[room_name][0][1] == None: # public and waiting
                conn.sendall(f"Joined room {room_name}".encode())
                break
            elif room_name not in self.rooms:   # No such room
                conn.sendall("ERROR Room not found".encode())
            elif self.rooms[room_name][3] == "0": # private
                conn.sendall("ERROR Room is private".encode())
            elif self.rooms[room_name][2] == "1": # playing
                conn.sendall("ERROR Room is full".encode())
            else:
                conn.sendall("ERROR Room not found".encode())
        
        clientname = conn.recv(1024).decode()
        # Find the room and add the player
        host_conn = self.players[self.rooms[room_name][0][0]][0]
        host_conn.sendall(f"Request for IP and PORT".encode())
        print("Request for IP and PORT...")
        response = host_conn.recv(1024).decode()
        hostIP, hostPort = response.split()
        # Room: waiting to playing, fill player 2, fill Gameport(optional)
        self.rooms[room_name][0][1] = clientname
        self.rooms[room_name][4] = hostPort
        
        conn.sendall(f"{hostIP} {hostPort} {self.rooms[room_name][1]}".encode())
        
        # Wait for notification of game start
        print("\nWaiting for game start...")
        response = host_conn.recv(1024).decode()
        if response == "START":
            print("Game start...\n")
            self.players[clientname][2] = 1
            self.players[self.rooms[room_name][0][0]][2] = 1
            self.rooms[room_name][2] = 1
            
        # Wait for notification of game end
        print("\nWaiting for game end...")
        response = host_conn.recv(1024).decode()
        if response == "END":
            print("Game ended...\n")
            self.players[clientname][2] = 0 # status = waiting
            self.players[self.rooms[room_name][0][0]][2] = 0    # status = waiting
            del self.rooms[room_name]   # Delete the room

    def run_nothing(self, conn , addr):
        self.lock = 1

if __name__ == "__main__":
    server = LobbyServer()
    server.start()