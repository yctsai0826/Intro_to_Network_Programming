import socket
import time
import select
import signal
import sys
import subprocess
import shutil  # 用於複製文件
import os
import csv


SERVER_HOSTS = [
    "140.113.235.151",
    "140.113.235.152",
    "140.113.235.153",
    "140.113.235.154"
]

LobbyServer = "140.113.235.151"
LobbyPort = 11005

class GamePlayer:
    def __init__(self, host="140.113.235.154"):
        self.host = host
        self.username = None
        self.reconn = True
        self.invitations = []
        self.games = {}
        while True:
            port = input("Enter server port: ")
            if port.isdigit():
                port = int(port)
                if 10001 <= port <= 65535:
                    break
                else:
                    print("Port must be between 10001 and 65535. Please try again.")
            else:
                print("Invalid input. Please enter a number.")
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((LobbyServer, port))
            print("\n!!! Connected to the Lobby Server successfully. !!!\n")
            print("-----------------------------------------------------------------------\n")
        except socket.error as e:
            print(f"\n!!! Failed to connect to the Lobby Server: {e} !!!\n")
            print("-----------------------------------------------------------------------\n")
            sys.exit(1)  # Exit if the connection fails
        
        signal.signal(signal.SIGINT, self.handle_exit)  # Register signal handler for Ctrl+C

    def download_game_script(self, game_name):
        # 定義腳本來源路徑和目標路徑
        source_path = f"../server/game_file/{game_name}.py"
        destination_path = f"./download/{game_name}.py"

        # 檢查目標目錄是否存在，若不存在則創建
        destination_dir = os.path.dirname(destination_path)
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)

        # 確保源文件存在
        if not os.path.exists(source_path):
            print(f"\n!!! Game script {game_name}.py not found in ../server/game_file/. !!!\n")
            return None

        # 獲取文件大小以計算進度
        file_size = os.path.getsize(source_path)

        print(f"\nDownloading game script: {game_name}.py\n")
        with open(source_path, "rb") as src_file, open(destination_path, "wb") as dest_file:
            downloaded = 0  # 初始化下載大小
            while True:
                chunk = src_file.read(1024)
                if not chunk:
                    break
                dest_file.write(chunk)
                downloaded += len(chunk)
                
                # 計算進度百分比
                progress = int((downloaded / file_size) * 100)
                print(f"\rProgress: {progress}% [{'=' * (progress // 2)}{' ' * (50 - progress // 2)}]", end="")
        
        print(f"\n\nDownloaded game script: {destination_path}\n")
        return destination_path
    
    def run_game_script(self, script_path, is_host, game_ip, game_port):
        host_flag = "1" if is_host else "0"  # 主機為 1，否則為 0
        print(f"\nRunning game script: {script_path}")
        subprocess.run(["python", script_path, host_flag, game_ip, str(game_port)])
    
    def handle_exit(self, signum, frame):
        print("\nExiting...")
        self.send_message(f"INTERRUPT {self.username}")
        time.sleep(0.1)
        self.send_message(f"INTERRUPT {self.username}")
        time.sleep(0.1)
        self.client.close()
        sys.exit(0)  # Exit gracefully
    
    def send_message(self, msg):
        try:
            self.client.sendall(msg.encode())
        except BrokenPipeError:
            print("Connection lost. Attempting to reconnect...")
            if self.reconnect():  # 假設有一個 reconnect 函數處理重連
                self.client.sendall(msg.encode())
            else:
                print("Failed to reconnect. Please try again later.")

    def reconnect(self):
        print("\n!!! Attempting to reconnect to the Lobby Server using the original IP and port... !!!\n")
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # 從現有連線中取得本地的 host 和 port
                # print(self.client)
                local_host, local_port = self.client.getsockname()
                # print(f"Local host: {local_host}, Local port: {local_port}")
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.bind((local_host, local_port))  # 使用原來的本地 IP 和 port
                self.client.connect((LobbyServer, LobbyPort))
                print("\n!!! Successfully reconnected to the Lobby Server using the original IP and port !!!\n")
                print("\n!!! Please try again. !!!\n")
                # print("-----------------------------------------------------------------------\n")
                # print(self.client)
                return True
            except socket.error as e:
                print(f"\n!!! Reconnection attempt {attempt + 1}/{max_retries} failed: {e} !!!\n")
                print("Retrying...")
                time.sleep(2)  # 等待 2 秒後再試
        print("\n!!! Could not reconnect to the riLobby Server after multiple attempts. !!!\n")
        return False

    def register(self):
        while True:
            while True:
                username = input("Enter username: ")
                if username != "":
                    break
                else:
                    print("\n!!! Username cannot be empty. Please try again. !!!\n")
                    print("-----------------------------------------------------------------------\n")
            while True:
                password = input("Enter password: ")
                if password != "":
                    break
                else:
                    print("\n!!! Password cannot be empty. Please try again. !!!\n")
                    print("-----------------------------------------------------------------------\n")
            self.send_message(f"REGISTER {username} {password}")
            # 接收伺服器回覆
            response = self.client.recv(1024).decode()
            if response == "SUCCESS Registered":
                print("\n!!! Registration successful !!!\n")
                print("-----------------------------------------------------------------------\n")
                return
            elif response =="ERROR Username already exists":
                print(f"\n!!! {response}. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")
            else:
                print("\n!!! Unexpected server response. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")

    def login(self):
        while True:
            while True:
                username = input("Enter username: ")
                if username != "":
                    break
                else:
                    print("\n!!! Username cannot be empty. Please try again. !!!\n")
                    print("-----------------------------------------------------------------------\n")
            self.send_message(f"LOGIN {username}")
            response = self.client.recv(1024).decode()
            if response.startswith("ERROR"):
                print(f"\n!!! {response}. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")
            else:
                self.username = username
                break
        while True:
            while True:
                password = input("Enter password: ")
                if password != "":
                    break
                else:
                    print("\n!!! Password cannot be empty. Please try again. !!!\n")
                    print("-----------------------------------------------------------------------\n")
            self.send_message(f"{password}")
            response = self.client.recv(1024).decode()
            if response == "SUCCESS Logged in":
                print("\n!!! Login successful !!!\n")
                print("-----------------------------------------------------------------------\n")
                response = self.client.recv(1024).decode()
                print(response)
                self.list_rooms()
                return
            else:
                print("\n!!! Incorrect password. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")
        
    def select_game_type(self):
        game_data_csv = "../server/game_data.csv"

        # 檢查遊戲數據文件是否存在
        if not os.path.exists(game_data_csv):
            print("\n!!! No games available. The game data file does not exist. !!!\n")
            return None

        # 讀取遊戲數據文件
        with open(game_data_csv, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            games = list(reader)

            if not games:
                print("\n!!! No games available in the data file. !!!\n")
                return None

        # 動態生成遊戲選項
        print("\nAvailable games:")
        game_map = {}
        for idx, game in enumerate(games, start=1):
            print(f"{idx}. {game['game_name']} - {game['description']}")
            game_map[str(idx)] = game['game_name']
            self.games[str(idx)] = game['game_name']

        choice = input("\nEnter the number of the game you want to play: ")
        # 輸入選擇
        if choice in game_map:
                return choice
        else:
            print("\n!!! Invalid choice. Please select a valid game number. !!!\n")

    def create_room(self):
        self.send_message(f"CREATE_ROOM")
        while True:
            while True:
                room_name = input("Enter room name: ")
                if room_name != "":
                    break
                else:
                    print("\n!!! Room name cannot be empty. Please try again. !!!\n")
                    print("-----------------------------------------------------------------------\n")
            self.send_message(f"{room_name} {self.username}")
            response = self.client.recv(1024).decode()
            if response == f"Room {room_name} created":
                print(f"\n!!! Room {room_name} created !!!\n")
                break
            elif response == "ERROR Room already exists":
                print(f"\n!!! {response}. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")
            else:
                print("\n!!! Unexpected server response. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")
        
        while True:
            game_type = self.select_game_type()
            if game_type:
                break
            cmd = input("No available games. Type any key to re-select")

        if not game_type:
            print("\n!!! Room creation canceled due to no valid game selection. !!!\n")
            return
        
        self.download_game_script(self.games[game_type])
                
        while True:
            public = input("Is the room public? (y/n): ")
            if public in ["y", "n"]:
                break
            else:
                print("\n!!! Invalid input. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")

        public = "1" if public == "y" else "0"
        while True:
            game_port_input = input("Enter game port to bind (10001 ~ 65535): ").strip()
            if game_port_input.isdigit():
                GamePort = int(game_port_input)
                if 10001 <= GamePort <= 65535:
                    break  # Valid port; exit the loop
                else:
                    print("Port must be between 10001 and 65535. Please try again.")
            else:
                print("Invalid input. Please enter a number.")

        GameIP = self.host
        self.send_message(f"{game_type} {public}")
        response = self.client.recv(1024).decode()
        print(f"Private_room.{response=}")
        if response == "SUCCESS Room created" and public == "1":
            print("\n!!! Public room created successfully. Waiting for other players to join... !!!\n")
            print("-----------------------------------------------------------------------\n")
            response = self.client.recv(1024).decode()
            if response == "Start game?":
                print("The room is full.")
                change = input("Do you want to change the game? (y/n)")
                if change == "y":
                    while True:
                        game_type = self.select_game_type()
                        if game_type:
                            break
                        cmd = input("No available games. Type any key to re-select")
                    self.download_game_script(self.games[game_type])
                while True:
                    ans = input("Start the game? (y/n)")
                    if ans == "y":
                        self.send_message("Start")
                        time.sleep(0.1)
                        self.send_message("Start")
                        time.sleep(0.1)
                        break
            response = self.client.recv(1024).decode()  # Wait for other players to join
            if response == "Request for IP and PORT":
                self.send_message(f"{GameIP} {GamePort}")
                time.sleep(0.1)
                print("!!! Receive request for IP and PORT !!!\n")
                print("-----------------------------------------------------------------------\n")
                # Create game TCP server
                time.sleep(0.1)
                self.send_message("START")
                time.sleep(0.1)
                self.send_message("START")
                self.run_game_script(f"./download/{self.games[game_type]}.py", True, GameIP, GamePort)
                self.send_message("END")
                time.sleep(0.3)
                self.send_message("END")
                time.sleep(0.3)
            else:
                print(f"\n!!! Unexpected server response: {response}. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")
                
        elif response == "SUCCESS Room created" and public == "0":
            print("\n!!! Private room created successfully. Waiting for other players to join... !!!\n")
            response = self.client.recv(1024).decode()  # Idle players information
            print("-----------------------------------------------------------------------\n")
            print(response)
            print("-----------------------------------------------------------------------\n")
            while True:
                while True:
                    command = input("Your choice? (1. send invitation 2. list idle players): ")
                    if command in ["1", "2"]:
                        break
                    else:
                        print("\n!!! Invalid input. Please try again. !!!\n")
                        print("-----------------------------------------------------------------------\n")
                if (command == "1"):
                    while True:
                        clientname = input("Send invitation to (enter player's name): ")
                        if clientname != "":
                            break
                        else:
                            print("\n!!! Player's name cannot be empty. Please try again. !!!\n")
                            print("-----------------------------------------------------------------------\n")
                    self.send_message(f"{clientname}")
                    response = self.client.recv(1024).decode()
                    print(f"{response=}")
                    if response == f"Invited {clientname}":
                        print(f"\n!!! Invitation sent to {clientname} !!!\n")
                        print("-----------------------------------------------------------------------\n")
                        
                        print("Wait for lock...")
                        response = self.client.recv(1024).decode()
                        if response == "unlock":
                            self.send_message("unlock")
                        
                        response = self.client.recv(1024).decode()
                        print(f"{response=}")
                        if response == "ACCEPTED":
                            print(f"\n!!! {clientname} accepted the invitation. Game starting... !!!\n")
                            print("-----------------------------------------------------------------------\n")
                            break
                        elif response == "REJECTED":
                            print(f"\n!!! {clientname} rejected the invitation. Please try again. !!!\n")
                            print("-----------------------------------------------------------------------\n")
                            continue
                    elif response == "ERROR User not found or not available":
                        print(f"\n!!! {response}. Please try again. !!!\n")
                        print("-----------------------------------------------------------------------\n")
                    else:
                        print("\n!!! Unexpected server response. Please try again. !!!\n")
                        print("-----------------------------------------------------------------------\n")
                elif (command == "2"):
                    self.send_message("LIST_IDLE_PLAYERS")
                    response = self.client.recv(1024).decode()
                    print("-----------------------------------------------------------------------\n")
                    print(response)
                    print("-----------------------------------------------------------------------\n")
            
            # Start the game?
            response = self.client.recv(1024).decode()
            if response == "Start game?":
                print("The room is full.")
                change = input("Do you want to change the game? (y/n)")
                if change == "y":
                    while True:
                        game_type = self.select_game_type()
                        if game_type:
                            break
                        cmd = input("No available games. Type any key to re-select")
                    self.download_game_script(self.games[game_type])
                while True:
                    ans = input("Start the game? (y/n)")
                    if ans == "y":
                        self.send_message("Start")
                        break
            # Wait for client to accept invitation
            response = self.client.recv(1024).decode()
            if response == "Request for IP and PORT":
                time.sleep(0.1)
                print("!!! Receive request for IP and PORT !!!\n")
                self.send_message(f"{GameIP} {GamePort}")
                print("-----------------------------------------------------------------------\n")
                time.sleep(0.1)
                self.send_message(f"START")
                # Create game TCP server
                if (game_type == "1"):
                    self.run_game_script(f"./download/{self.games[game_type]}.py", True, GameIP, GamePort)
                    self.send_message("END")
                    time.sleep(0.3)
                    self.send_message("END")
                    time.sleep(0.3)
                elif (game_type == "2"):
                    self.run_game_script(f"./download/{self.games[game_type]}.py", True, GameIP, GamePort)
                    self.send_message("END")
                    time.sleep(0.3)
                    self.send_message("END")
                    time.sleep(0.3)
                
    def join_room(self):
        self.send_message(f"JOIN_ROOM")
        while True:
            while True:
                room_name = input("Enter room name: ")
                if room_name != "":
                    break
                else:
                    print("\n!!! Room name cannot be empty. Please try again. !!!\n")
                    print("-----------------------------------------------------------------------\n")
            self.send_message(f"{room_name}")
            response = self.client.recv(1024).decode()
            if response == f"Joined room {room_name}":
                print(f"\n!!! Trying to join room [{room_name}] !!!\n")
                break
            elif response.startswith("ERROR"):
                print(f"\n!!! {response}. Please try again. !!!\n")
            else:
                print("\n!!! Unexpected server response. Please try again. !!!\n")
        self.send_message(f"{self.username}")
        response = self.client.recv(1024).decode()
        GameIP, GamePort, GameType = response.split()
        self.renew_game_data()
        self.download_game_script(self.games[GameType])
        GamePort = int(GamePort)
        time.sleep(0.5)
        if (GameType == "1"):
            self.run_game_script(f"./download/{self.games[GameType]}.py", False, GameIP, GamePort)
        elif (GameType == "2"):
            self.run_game_script(f"./download/{self.games[GameType]}.py", False, GameIP, GamePort)
                
    def list_rooms(self):
        try:
            self.send_message("LIST_ROOMS")
            response = self.client.recv(1024).decode()
            print("\n-----------------------------------------------------------------------\n")
            print("\n!!! Listing players and rooms... !!!\n")
            print(response)
            print("\n-----------------------------------------------------------------------\n")
        except ConnectionResetError:
            print("Connection to the server was reset. Attempting to reconnect...")
            if self.reconnect():
                self.list_rooms()
            else:
                print("Failed to reconnect.")
                self.reconn = False

    def logout(self):
        self.send_message(f"LOGOUT {self.username}")
        response = self.client.recv(1024).decode()
        if response == "SUCCESS Logged out":
            print("\n!!! Logout successful !!!\n")
            print("-----------------------------------------------------------------------\n")
        else:
            print("\n!!! Logout failed. Please try again. !!!\n")
            print("-----------------------------------------------------------------------\n")

    def check_game_over(self, board, row, col, player, connect_four=False):
        if connect_four:
            win_cond = 4
            width, height = 7, 6
        else:
            win_cond = 5
            width, height = 15, 15
            
            
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # 右, 下, 右下斜, 左下斜
        for dr, dc in directions:
            count = 1  # 包括自己
            # 向一个方向检查
            for i in range(1, win_cond):
                r, c = row + dr * i, col + dc * i
                if 0 <= r < height and 0 <= c < width and board[r][c] == player:
                    count += 1
                else:
                    break
            # 向相反方向检查
            for i in range(1, win_cond):
                r, c = row - dr * i, col - dc * i
                if 0 <= r < height and 0 <= c < width and board[r][c] == player:
                    count += 1
                else:
                    break
            if count >= win_cond:
                return True
        return False
    
    def receive_invitation(self, msg):
        try:
            if msg.startswith("Invited to"):
                room_name = msg.split()[2]
                print(f"\n!!! You have received an invitation to join [{room_name}] !!!")
                self.invitations.append(room_name)  # 將邀請存入陣列
                print(f"Invitation to [{room_name}] has been added to your invitations list.")
        except Exception as e:
            print(f"Error while receiving invitation: {e}")
            
    def view_invitations(self):
        print("-----------------------------------------------------------------------\n")
        if not self.invitations:
            print("\n!!! No invitations available. !!!\n")
            return

        print("\n!!! Invitations List !!!\n")
        for i, room in enumerate(self.invitations, 1):
            print(f"{i}. {room}")
    
    def renew_game_data(self):
        game_data_csv = "../server/game_data.csv"

        if not os.path.exists(game_data_csv):
            return None

        # 讀取遊戲數據文件
        with open(game_data_csv, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            games = list(reader)

            if not games:
                return None

        # 動態生成遊戲選項
        for idx, game in enumerate(games, start=1):
            print(f"{idx}. {game['game_name']} - {game['description']}")
            self.games[str(idx)] = game['game_name']
            
    def accept_invitation(self, room):
        try:
            self.send_message(f"{room}")
            time.sleep(0.1)
            while True:
                acc = input("Accept the invitation? (y/n): ")
                self.invitations.remove(room)
                if acc in ["y", "n"]:
                    break
                else:
                    print("Invalid input. Please enter 'y' or 'n'.")
            if acc == "y":
                self.send_message(f"ACCEPT {room}")
                time.sleep(0.2)
                self.send_message(f"ACCEPT {room}")
                time.sleep(0.2)
                TCPinfo = self.client.recv(1024).decode()
                print(f"Received TCP info: {TCPinfo}")
                GameIP, GamePort, Gametype = TCPinfo.split()
                GamePort = int(GamePort)
                self.renew_game_data()
                self.download_game_script(self.games[Gametype])
                time.sleep(0.5)
                if (Gametype == "1"):
                    self.run_game_script(f"./download/{self.games[Gametype]}.py", False, GameIP, GamePort)
                elif (Gametype == "2"):
                    self.run_game_script(f"./download/{self.games[Gametype]}.py", False, GameIP, GamePort)
            else:
                self.send_message("REJECT")
        except Exception as e:
            print(f"Error while receiving invitation: {e}")
        finally:
            # 清空緩衝區
            self.clear_socket_buffer()
            
    def invitation_management(self):
        while True:
            print("-----------------------------------------------------------------------\n")
            print("Welcone to Invitation Management:")
            print("1. List all invitation")
            print("2. Accept/Reject invitation")
            print("3. Leave")
            cmd = input("Enter your choice: ")
            if cmd not in ["1", "2", "3"]:
                print("\n!!! Invalid command !!!\n")
                continue
            if cmd == "1":
                self.view_invitations()
            elif cmd == "2":
                self.send_message("INVITATION")
                room_name = input("Enter the room name you want to enter: ")
                self.accept_invitation(room=room_name)
            elif cmd == "3":
                print("Leaving invitation management...\n")
                break         

    def clear_socket_buffer(self):
        """清空 socket 接收緩衝區。"""
        self.client.setblocking(0)  # 設定為非阻塞模式
        try:
            while True:
                data = self.client.recv(1024)
                if not data:
                    break  # 沒有更多資料
        except BlockingIOError:
            pass  # 非阻塞模式下無更多資料
        finally:
            self.client.setblocking(1)  # 恢復為阻塞模式


    def upload_game(self, filename, description):
        source_path = f"./{filename}.py"
        destination_dir = "../server/game_file/"
        game_data_csv = "../server/game_data.csv"

        # 確認遊戲腳本存在
        if not os.path.exists(source_path):
            print(f"\n!!! Game file {filename}.py does not exist. !!!\n")
            return

        # 確保目標目錄存在
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)

        # 將遊戲腳本複製到目標目錄
        destination_path = os.path.join(destination_dir, f"{filename}.py")
        shutil.copy(source_path, destination_path)
        print(f"\n!!! Successfully uploaded {filename}.py to server !!!\n")

        # 更新 CSV 文件，刪除相同名稱的遊戲記錄（如果存在）
        updated_records = []
        if os.path.exists(game_data_csv):
            with open(game_data_csv, "r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                headers = reader.fieldnames
                for row in reader:
                    if row["game_name"] != filename:  # 避免重複添加
                        updated_records.append(row)
        else:
            # 如果文件不存在，創建標題行
            headers = ["game_name", "author", "description", "comments", "ratings"]

        # 添加新的遊戲資訊，初始 comments 為空
        new_game_info = {
            "game_name": filename,
            "author": self.username,
            "description": description,
            "comments": "",
            "ratings": ""
        }
        updated_records.append(new_game_info)

        # 寫入更新後的記錄
        with open(game_data_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()  # 寫入標題行
            writer.writerows(updated_records)  # 寫入所有記錄

        print(f"!!! Game information updated and saved to {game_data_csv} !!!\n")



    def list_all_game(self):
        game_data_csv = "../server/game_data.csv"

        if not os.path.exists(game_data_csv):
            print("\n!!! No games found. The game data file does not exist. !!!\n")
            return

        with open(game_data_csv, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            if not rows:
                print("\n!!! No games found in the data file. !!!\n")
                return

            # Headers 包含 comments 和 ratings
            headers = ["Game Name", "Author", "Description", "Comments", "Ratings"]
            column_widths = [len(header) for header in headers]
            for row in rows:
                column_widths[0] = max(column_widths[0], len(row["game_name"]))
                column_widths[1] = max(column_widths[1], len(row["author"]))
                column_widths[2] = max(column_widths[2], len(row["description"]))
                column_widths[3] = max(column_widths[3], len(row.get("comments", "")))
                column_widths[4] = max(column_widths[4], len(row.get("ratings", "")))

            # Print headers
            print("\n" + " | ".join(header.ljust(width) for header, width in zip(headers, column_widths)))
            print("-" * (sum(column_widths) + len(headers) - 1))  # Adjust for column spacing

            # Print rows
            for row in rows:
                print(
                    f"{row['game_name'].ljust(column_widths[0])} | "
                    f"{row['author'].ljust(column_widths[1])} | "
                    f"{row['description'].ljust(column_widths[2])} | "
                    f"{row.get('comments', '').ljust(column_widths[3])} | "
                    f"{row.get('ratings', '').ljust(column_widths[4])}"
                )

    def comment_on_game(self):
        game_data_csv = "../server/game_data.csv"

        # 檢查遊戲數據文件是否存在
        if not os.path.exists(game_data_csv):
            print("\n!!! Game data file does not exist. !!!\n")
            return

        # 加載遊戲列表
        games = []
        with open(game_data_csv, "r", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader, None)  # 獲取標題行
            if headers and "comments" not in headers:
                headers.append("comments")  # 添加 "comments" 列標題
            if headers and "ratings" not in headers:
                headers.append("ratings")  # 添加 "ratings" 列標題
            for row in reader:
                while len(row) < 5:  # 確保有足夠的列
                    row.append("")
                games.append(row)

        # 顯示遊戲列表
        print("\nAvailable games:")
        for idx, game in enumerate(games, 1):
            print(f"{idx}. {game[0]} - {game[2]}")

        # 選擇遊戲
        while True:
            try:
                choice = int(input("\nEnter the number of the game you want to comment on: "))
                if 1 <= choice <= len(games):
                    break
                else:
                    print("\n!!! Invalid choice. Please select a valid game number. !!!\n")
            except ValueError:
                print("\n!!! Please enter a valid number. !!!\n")

        # 輸入評論
        comment = input(f"\nEnter your comment for {games[choice - 1][0]}: ").strip()
        if not comment:
            print("\n!!! Comment cannot be empty. !!!\n")
            return

        # 輸入評分
        while True:
            try:
                rating = int(input(f"\nEnter your rating for {games[choice - 1][0]} (1-5): "))
                if 1 <= rating <= 5:
                    break
                else:
                    print("\n!!! Invalid rating. Please enter a number between 1 and 5. !!!\n")
            except ValueError:
                print("\n!!! Please enter a valid number. !!!\n")

        # 更新評論列
        if games[choice - 1][3]:
            games[choice - 1][3] += f" | {self.username}: {comment}"  # 如果已有評論，追加
        else:
            games[choice - 1][3] = f"{self.username}: {comment}"

        # 更新評分列
        if games[choice - 1][4]:
            games[choice - 1][4] += f" | {self.username}: {rating}"  # 如果已有評分，追加
        else:
            games[choice - 1][4] = f"{self.username}: {rating}"

        # 保存更新到CSV
        with open(game_data_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            if headers:
                writer.writerow(headers)  # 寫入標題行
            writer.writerows(games)  # 寫入遊戲數據

        print("\n!!! Your comment and rating have been saved. !!!\n")


            

if __name__ == "__main__":
    player = GamePlayer()
    login = False
    while True:
        if player.reconn == False:
            print("Connection lost.")
            break
        print("Please select an option:")
        if not login:
            print("1. Register")
            print("2. Login")
            print("3. Exit")
        else:
            print("1. Logout")
            print("2. List rooms")
            print("3. Create room")
            print("4. Join room")
            print("5. Invitation management")
            print("6. Upload new game")
            print("7. List all games")
            print("8. Comment on a game")
            
        while True:
            cmd = input("Enter number: ")
            if not login and cmd in ["1", "2", "3"]:
                break
            elif login and cmd in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                break
            else:
                print("Invalid input. Please enter a valid number.")

        # Register
        if not login and cmd == "1":
            player.register()
        # Log in
        elif not login and cmd == "2":
            player.login()
            login = True
        # Exit
        elif not login and cmd == "3":
            print("!!! Exit game !!!")
            player.send_message(f"EXIT {player.username}")
            player.client.close()
            break
        # Log out
        elif login and cmd == "1":
            try:
                player.client.settimeout(0.1)  # 設置超時時間
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                
                # 將消息按換行符分割
                messages = msg.split('\n')
                for single_msg in messages:
                    if single_msg.strip():  # 確保消息非空
                        # 判斷消息類型並處理
                        if single_msg.startswith("Invited to"):
                            player.receive_invitation(single_msg)  # 處理邀請消息
                        elif single_msg.startswith("BROADCAST"):
                            print('\n')
                            print(single_msg)  # 處理廣播消息
            except socket.timeout:
                pass
            except ConnectionResetError:
                print("Connection was reset by the server. Attempting to reconnect...")
                if player.reconnect():
                    continue  # 成功重新連接後繼續操作
                else:
                    print("Failed to reconnect.")
                    break  # 終止程式
            finally:
                player.client.settimeout(None)

            player.logout()
            login = False
        # List rooms
        elif login and cmd == "2":
            try:
                player.client.settimeout(0.1)  # 設置超時時間
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                
                # 將消息按換行符分割
                messages = msg.split('\n')
                for single_msg in messages:
                    if single_msg.strip():  # 確保消息非空
                        # 判斷消息類型並處理
                        if single_msg.startswith("Invited to"):
                            player.receive_invitation(single_msg)  # 處理邀請消息
                        elif single_msg.startswith("BROADCAST"):
                            print('\n')
                            print(single_msg)  # 處理廣播消息
            except socket.timeout:
                pass
            except ConnectionResetError:
                print("Connection was reset by the server. Attempting to reconnect...")
                if player.reconnect():
                    continue  # 成功重新連接後繼續操作
                else:
                    print("Failed to reconnect.")
                    break  # 終止程式
            finally:
                player.client.settimeout(None)
            player.list_rooms()

        # Create room
        elif login and cmd == "3":
            try:
                player.client.settimeout(0.1)  # 設置超時時間
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                
                # 將消息按換行符分割
                messages = msg.split('\n')
                for single_msg in messages:
                    if single_msg.strip():  # 確保消息非空
                        # 判斷消息類型並處理
                        if single_msg.startswith("Invited to"):
                            player.receive_invitation(single_msg)  # 處理邀請消息
                        elif single_msg.startswith("BROADCAST"):
                            print('\n')
                            print(single_msg)  # 處理廣播消息
            except socket.timeout:
                pass
            except ConnectionResetError:
                print("Connection was reset by the server. Attempting to reconnect...")
                if player.reconnect():
                    continue  # 成功重新連接後繼續操作
                else:
                    print("Failed to reconnect.")
                    break  # 終止程式
            finally:
                player.client.settimeout(None)
            player.create_room()
        # Join room
        elif login and cmd == "4":
            try:
                player.client.settimeout(0.1)  # 設置超時時間
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                
                # 將消息按換行符分割
                messages = msg.split('\n')
                for single_msg in messages:
                    if single_msg.strip():  # 確保消息非空
                        # 判斷消息類型並處理
                        if single_msg.startswith("Invited to"):
                            player.receive_invitation(single_msg)  # 處理邀請消息
                        elif single_msg.startswith("BROADCAST"):
                            print('\n')
                            print(single_msg)  # 處理廣播消息
            except socket.timeout:
                pass
            except ConnectionResetError:
                print("Connection was reset by the server. Attempting to reconnect...")
                if player.reconnect():
                    continue  # 成功重新連接後繼續操作
                else:
                    print("Failed to reconnect.")
                    break  # 終止程式
            finally:
                player.client.settimeout(None)
            player.join_room()
        elif login and cmd == "5":
            try:
                player.client.settimeout(0.1)  # 設置超時時間
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                
                # 將消息按換行符分割
                messages = msg.split('\n')
                for single_msg in messages:
                    if single_msg.strip():  # 確保消息非空
                        # 判斷消息類型並處理
                        if single_msg.startswith("Invited to"):
                            player.receive_invitation(single_msg)  # 處理邀請消息
                        elif single_msg.startswith("BROADCAST"):
                            print('\n')
                            print(single_msg)  # 處理廣播消息
            except socket.timeout:
                pass
            except ConnectionResetError:
                print("Connection was reset by the server. Attempting to reconnect...")
                if player.reconnect():
                    continue  # 成功重新連接後繼續操作
                else:
                    print("Failed to reconnect.")
                    break  # 終止程式
            finally:
                player.client.settimeout(None)
            player.invitation_management()
        elif login and cmd == "6":
            try:
                player.client.settimeout(0.1)  # 設置超時時間
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                
                # 將消息按換行符分割
                messages = msg.split('\n')
                for single_msg in messages:
                    if single_msg.strip():  # 確保消息非空
                        # 判斷消息類型並處理
                        if single_msg.startswith("Invited to"):
                            player.receive_invitation(single_msg)  # 處理邀請消息
                        elif single_msg.startswith("BROADCAST"):
                            print('\n')
                            print(single_msg)  # 處理廣播消息
            except socket.timeout:
                pass
            except ConnectionResetError:
                print("Connection was reset by the server. Attempting to reconnect...")
                if player.reconnect():
                    continue  # 成功重新連接後繼續操作
                else:
                    print("Failed to reconnect.")
                    break  # 終止程式
            finally:
                player.client.settimeout(None)
            filename = input("Enter the game file name: ")
            description = input("Enter the game description: ")
            player.upload_game(filename, description)
        elif login and cmd == "7":
            try:
                player.client.settimeout(0.1)  # 設置超時時間
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                
                # 將消息按換行符分割
                messages = msg.split('\n')
                for single_msg in messages:
                    if single_msg.strip():  # 確保消息非空
                        # 判斷消息類型並處理
                        if single_msg.startswith("Invited to"):
                            player.receive_invitation(single_msg)  # 處理邀請消息
                        elif single_msg.startswith("BROADCAST"):
                            print('\n')
                            print(single_msg)  # 處理廣播消息
            except socket.timeout:
                pass
            except ConnectionResetError:
                print("Connection was reset by the server. Attempting to reconnect...")
                if player.reconnect():
                    continue  # 成功重新連接後繼續操作
                else:
                    print("Failed to reconnect.")
                    break  # 終止程式
            finally:
                player.client.settimeout(None)
            player.client.settimeout(None)
            player.list_all_game()
            
        elif login and cmd == "8":
            try:
                player.client.settimeout(0.1)  # 設置超時時間
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                
                # 將消息按換行符分割
                messages = msg.split('\n')
                for single_msg in messages:
                    if single_msg.strip():  # 確保消息非空
                        # 判斷消息類型並處理
                        if single_msg.startswith("Invited to"):
                            player.receive_invitation(single_msg)  # 處理邀請消息
                        elif single_msg.startswith("BROADCAST"):
                            print('\n')
                            print(single_msg)  # 處理廣播消息
            except socket.timeout:
                pass
            except ConnectionResetError:
                print("Connection was reset by the server. Attempting to reconnect...")
                if player.reconnect():
                    continue  # 成功重新連接後繼續操作
                else:
                    print("Failed to reconnect.")
                    break  # 終止程式
            finally:
                player.client.settimeout(None)
            player.client.settimeout(None)
            player.comment_on_game()
        else:
            print("Invalid command")
            continue

