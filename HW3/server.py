import socket
import threading
import time
import csv
import os

SERVER_HOSTS = [
    "140.113.235.151",
    "140.113.235.152",
    "140.113.235.153",
    "140.113.235.154"
]

class LobbyServer:
    def __init__(self, host="127.0.0.1", port=11005, BCPort = 11010):
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
                
        try:
            self.BCserver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.BCserver.bind((host, BCPort))
            self.BCserver.listen(5)
            print(f"Boardcast Lobby Server started on {host}:{BCPort}")
        except socket.error as e:
            print(f"Error starting BCserver on port {BCPort}: {e}")
            BCPort += 1
            print(f"Retrying with port {BCPort}...")
                
            
        self.clients = {}  # {username: (conn, addr, password)}
        self.players = {}  # {username: [conn, addr, status, BCconn]}
        self.rooms = {}  # {room_name: [[client1, client2], game_type, status, private/public, Gameport]}
        self.lock = 0
        self.accounts_file = "./accounts.csv"  # 儲存帳號密碼的檔案
        self.load_accounts()
        
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
                        
                elif msg.startswith("LOGOUT"):
                    username = msg.split()[1]
                    print("logging out...")
                    self.players[username][2] = -1
                    self.broadcast(f"BROADCAST: {username} has exited.")
                    del self.players[username]
                    conn.sendall("SUCCESS Logged out".encode())
                
                elif msg == "LIST_ROOMS":
                    self.list_rooms(conn, addr)
                    
                elif msg == "INVITATION":
                    self.invitation_management(conn)
                
                elif msg.startswith("EXIT"):
                    user = msg.split()[1]
                    print("Exiting.")
                
                elif msg.startswith("INTERRUPT"):
                    user = msg.split()[1]
                    self.handle_interrupt(user)
                    
                elif msg == "NOTHING":
                    self.run_nothing(conn, addr)

                            
                else:
                    time.sleep(1.5)
                    
        except (ConnectionResetError, BrokenPipeError):
            print(f"Client {addr} disconnected.")
            if username:
                self.cleanup_user(username)
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            
        finally:
            conn.close()
            
    def load_accounts(self):
        self.accounts = {}
        if os.path.exists(self.accounts_file):
            with open(self.accounts_file, mode="r", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) == 2:  # 檢查格式是否正確
                        username, password = row
                        self.clients[username] = [None, None, password]
        print(f"Loaded accounts: {len(self.clients)} users")

    def save_account(self, username, password):
        with open(self.accounts_file, mode="a", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([username, password])
       
    def broadcast(self, message):
        print(f"Broadcasting: {message}")
        for username, data in self.players.items():
            BCconn = data[3]  # 獲取廣播連接
            if data[2] == 0 and BCconn:
                try:
                    print(f"Broadcasting to {username}: {message}")
                    BCconn.sendall(f"{message}".encode())
                    print(f"Broadcasted to {username}: {message}")
                except Exception as e:
                    print(f"Error broadcasting to {username}: {e}")
                    
    def send_invitation(self, message, BCconn):
        print(f"Sending Invitation: {message}")
        BCconn.sendall(f"{message}".encode())
        print(f"Invitation sent: {message}")

    def handle_interrupt(self, user):
        # Handle user interrupt by cleaning up associated rooms
        print("Handling user interrupt...")
        if user in self.players:
            for room_name in list(self.rooms.keys()):  # Traverse all room names
                if self.rooms[room_name][0][0] == user or self.rooms[room_name][0][1] == user:  # If the user is the host
                    if self.rooms[room_name][0][0] == user:
                        other_player = self.rooms[room_name][0][1]
                    elif self.rooms[room_name][0][1] == user:
                        other_player = self.rooms[room_name][0][0]
                    if other_player and other_player in self.players:
                        # Set the status of the other player to "waiting"
                        self.players[other_player][2] = 0
                    print(f"Deleting room: {room_name} hosted by {user}")
                    del self.rooms[room_name]  # Delete the room
            # Remove user from the players dictionary
            del self.players[user]
            print(f"User {user} removed from players.")

      
    def cleanup_user(self, username):
        if username in self.players:
            # Handle room cleanup if the user is a host
            for room_name, room_info in list(self.rooms.items()):
                if room_info[0][0] == username:  # Host is the user
                    del self.rooms[room_name]
            # Remove player from the players dictionary
            del self.players[username]

    def start(self):
        print("Lobby Server is running...")
        
        threading.Thread(target=self.run_broadcast_server, daemon=True).start()
        
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
            
    def run_broadcast_server(self):
        print("Broadcast Server is running...")
        while True:
            conn, addr = self.BCserver.accept()
            thread = threading.Thread(target=self.handle_broadcast_client, args=(conn, addr))
            thread.start()
            
    def handle_broadcast_client(self, conn, addr):
        print(f"New broadcast connection from {addr}")
        username = None
        try:
            while True:
                msg = conn.recv(1024).decode()
                if not msg:
                    break
                print(f"Broadcast client message: {msg}")
                if msg.startswith("REGISTER_BC"):
                    username = msg.split()[1]
                    if username in self.players:
                        self.players[username][3] = conn  # 設置廣播連接
                        conn.sendall("SUCCESS Registered for Broadcast".encode())
                    else:
                        conn.sendall("ERROR User not found".encode())
                elif msg == "EXIT_BC":
                    break
        except Exception as e:
            print(f"Error handling broadcast client: {e}")
        finally:
            conn.close()
            if username and username in self.players:
                self.players[username][3] = None
            print(f"Broadcast connection closed for {addr}")
                       
    def register(self, username, password, conn, addr):
        if username in self.clients:
            conn.sendall("ERROR Username already exists".encode())
            return False
        self.accounts[username] = password
        self.save_account(username, password)
        # Username available
        self.clients[username] = [conn, addr, password]     # 0 = waiting, 1 = playing, 2: In room
        conn.sendall("SUCCESS Registered".encode())
        return True
       
    def login(self, username, conn, addr):
        while True:
            if username in self.clients:
                conn.sendall("User exist.".encode())
                break
            elif username in self.players:
                conn.sendall("ERROR User is already logged in".encode())
                break
            elif username not in self.clients:
                conn.sendall("ERROR User does not exist".encode())
            msg = conn.recv(1024).decode()
            username = msg.split()[1]
        while True:
            password = conn.recv(1024).decode()
            if password == self.clients[username][2]:
                self.clients[username][0] = conn
                self.clients[username][1] = addr
                self.players[username] = [conn, addr, 0, None]
                time.sleep(0.1)
                conn.sendall("SUCCESS Logged in".encode())
                time.sleep(0.5)
                self.broadcast(f"BROADCAST: {username} has logged in.")
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
        time.sleep(0.3)
        self.players[host_name][2] = 2  # In room
        
        if public == "1":
            self.broadcast(f"BROADCAST: Room {room_name} created by {host_name}")
            leaveroom = conn.recv(1024).decode()
            if leaveroom == "LEAVE_ROOM":
                self.players[host_name][2] = 0
                del self.rooms[room_name]
                return
            return
        
        # Private room
        self.list_idle_players(conn, addr)
        
        while True:
            comm = conn.recv(1024).decode()
            print(f"{comm=}")
            if comm == "LIST_IDLE_PLAYERS":
                self.list_idle_players(conn, addr)
            elif comm == "LEAVE_ROOM":
                self.players[host_name][2] = 0
                del self.rooms[room_name]
                return
            else:
                client_name = comm
                client_conn = self.players[client_name][0]
                if client_name in self.players and self.players[client_name][2] == 0:   # waiting
                    conn.sendall(f"Invited {client_name}".encode())
                    print("Sending invitation...")
                    self.send_invitation(f"Invited to {room_name}", self.players[client_name][3])
                    # client_conn.sendall(f"Invited to {room_name}\n".encode())
                    response = conn.recv(1024).decode() # wait for player B's response
                    if response != "unlock":
                        continue
                    print(f"Unlock msg: {response}")
                    
                    print("Waiting for accept/reject response...")
                    response = client_conn.recv(1024).decode() # wait for player B's response
                    
                    print(f"{response=}")
                    if response == f"ACCEPT {room_name}":
                        self.players[client_name][2] = 2
                        self.rooms[room_name][0][1] = client_name
                        conn.sendall(f"ACCEPTED".encode())
                        break
                    else:
                        self.players[client_name][2] = 0
                        conn.sendall(f"REJECTED".encode())
                        continue
                conn.sendall("ERROR User not found or rejected".encode())
        
        time.sleep(0.1)
        conn.sendall(f"Start game?".encode())
        print("Asking host for game start...")
        response = conn.recv(1024).decode()
        if response == "Start":
            print("Game started by the host.")
        
        # Request for IP and PORT
        client_conn  = self.players[client_name][0]
        time.sleep(0.5)
        conn.sendall(f"Request for IP and PORT".encode())
        response = conn.recv(1024).decode()
        print(response)
        print(f"2.{response=}")
        hostIP, hostPort, game_type = response.split()
        self.rooms[room_name][1] = game_type
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
        elif response == "DISCONNECTED":
            print("Game disconnected...\n")
            self.players[client_name][2] = 0
            self.players[self.rooms[room_name][0][0]][2] = 0
            del self.rooms[room_name]
            return
        
        # Wait for notification of game end
        print("\nWaiting for game end...")
        response = conn.recv(1024).decode()
        print(f"end:{response=}")
        if response == "END" or response == "START":
            print("Game ended...\n")
            self.players[client_name][2] = 0 # status = waiting
            self.players[self.rooms[room_name][0][0]][2] = 0    # status = waiting
            del self.rooms[room_name]   # Delete the room
            print("Game ended...\n")
        elif response == "DISCONNECTED":
            print("Game disconnected...\n")
            self.players[client_name][2] = 0
            self.players[self.rooms[room_name][0][0]][2] = 0
            del self.rooms[room_name]
        self.players[host_name][2] = 0
        self.players[client_name][2] = 0
        self.players[self.rooms[room_name][0][0]][2] = 0
        del self.rooms[room_name]
        
        
    def list_idle_players(self, conn, addr):
        print("Listing idle players...")
        response = "\n"
        if self.players:
            player_list = "\n".join([
                f"    Username: [{username}]"
                for username, (conn, addr, status, BCconn) in self.players.items() if status == 0
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
                for username, (conn, addr, status, BCconn) in self.players.items()
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
        host_conn.sendall(f"Start game?".encode())
        print("Asking host for game start...")
        response = host_conn.recv(1024).decode()
        if response == "Start":
            print("Game started by the host.")
        
        host_conn.sendall(f"Request for IP and PORT".encode())
        print("Request for IP and PORT...")
        response = host_conn.recv(1024).decode()
        print(f"IP, PORT.{response=}")
        hostIP, hostPort, game_type = response.split()
        # Room: waiting to playing, fill player 2, fill Gameport(optional)
        self.rooms[room_name][0][1] = clientname
        self.rooms[room_name][4] = hostPort
        self.rooms[room_name][1] = game_type
        
        conn.sendall(f"{hostIP} {hostPort} {self.rooms[room_name][1]}".encode())
        
        # Wait for notification of game start
        print("\nWaiting for game start...")
        response = host_conn.recv(1024).decode()
        print(f"start.{response=}")
        if response == "START":
            print("Game start...\n")
            self.players[clientname][2] = 1
            self.players[self.rooms[room_name][0][0]][2] = 1
            self.rooms[room_name][2] = 1
        elif response == "DISCONNECTED":
            print("Game disconnected...\n")
            self.players[clientname][2] = 0
            self.players[self.rooms[room_name][0][0]][2] = 0
            del self.rooms[room_name]
            return
            
        # Wait for notification of game end
        print("\nWaiting for game end...")
        response = host_conn.recv(1024).decode()
        print(f"end.{response=}")
        if response == "END" or response == "START":
            self.lock = 0
            print("Game ended...\n")
            self.players[clientname][2] = 0 # status = waiting
            self.players[self.rooms[room_name][0][0]][2] = 0    # status = waiting
            del self.rooms[room_name]   # Delete the room
        elif response == "DISCONNECTED":
            print("Game disconnected...\n")
            self.players[clientname][2] = 0
            self.players[self.rooms[room_name][0][0]][2] = 0
            del self.rooms[room_name]
            return
        
    def run_nothing(self, conn , addr):
        self.lock = 1
        
    def invitation_management(self, conn):
        print("Waiting for room name...")
        response = conn.recv(1024).decode()
        print(f"Room name: {response}")
        if response in self.rooms:
            host_conn = self.players[self.rooms[response][0][0]][0]
            host_conn.sendall(f"unlock".encode())
            print("Unlocking room...")
        

if __name__ == "__main__":
    server = LobbyServer()
    server.start()
