import socket
import time
import select
import signal
import sys

SERVER_HOSTS = [
    "140.113.235.151",
    "140.113.235.152",
    "140.113.235.153",
    "140.113.235.154"
]

LobbyServer = "140.113.235.154"
LobbyPort = 11005

class GamePlayer:
    def __init__(self, host="140.113.235.154"):
        self.username = None
        port = int(input("Enter server port: "))
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect((host, port))
            print("\n!!! Connected to the Lobby Server successfully. !!!\n")
            print("-----------------------------------------------------------------------\n")
        except socket.error as e:
            print(f"\n!!! Failed to connect to the Lobby Server: {e} !!!\n")
            print("-----------------------------------------------------------------------\n")
            sys.exit(1)  # Exit if the connection fails
        
        signal.signal(signal.SIGINT, self.handle_exit)  # Register signal handler for Ctrl+C
    
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
            username = input("Enter username: ")
            password = input("Enter password: ")
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
            username = input("Enter username: ")
            self.send_message(f"LOGIN {username}")
            response = self.client.recv(1024).decode()
            if response.startswith("ERROR"):
                print(f"\n!!! {response}. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")
            else:
                self.username = username
                break
        while True:
            password = input("Enter password: ")
            self.send_message(f"{password}")
            response = self.client.recv(1024).decode()
            if response == "SUCCESS Logged in":
                print("\n!!! Login successful !!!\n")
                print("-----------------------------------------------------------------------\n")
                self.list_rooms()
                return
            else:
                print("\n!!! Incorrect password. Please try again. !!!\n")
                print("-----------------------------------------------------------------------\n")
        
    def create_room(self):
        self.send_message(f"CREATE_ROOM")
        while True:
            room_name = input("Enter room name: ")
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
        
        game_type = input("Enter game type (1: Gomoku, 2: Connect Four): ")
        public = input("Is the room public? (y/n): ")
        public = "1" if public == "y" else "0"
        GamePort = int(input("Enter game port to bind: "))
        GameIP = LobbyServer
        self.send_message(f"{game_type} {public}")
        response = self.client.recv(1024).decode()
        print(f"Private_room.{response=}")
        if response == "SUCCESS Room created" and public == "1":
            print("\n!!! Public room created successfully. Waiting for other players to join... !!!\n")
            print("-----------------------------------------------------------------------\n")
            response = self.client.recv(1024).decode()  # Wait for other players to join
            if response == "Request for IP and PORT":
                self.send_message(f"{GameIP} {GamePort}")
                time.sleep(0.1)
                print("!!! Receive request for IP and PORT !!!\n")
                print("-----------------------------------------------------------------------\n")
                # Create game TCP server
                if (game_type == "1"):
                    self.Game_1_p1(GameIP, GamePort, True)
                elif (game_type == "2"):
                    self.Game_2_p1(GameIP, GamePort, True)
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
                command = input("Your choice? (1. send invitation 2. list idle players): ")
                if (command == "1"):
                    clientname = input("Send invitation to (enter player's name): ")
                    self.send_message(f"{clientname}")
                    response = self.client.recv(1024).decode()
                    print(f"{response=}")
                    if response == f"Invited {clientname}":
                        print(f"\n!!! Invitation sent to {clientname} !!!\n")
                        print("-----------------------------------------------------------------------\n")
                        response = self.client.recv(1024).decode()
                        print(f"{response=}")
                        if response == "ACCEPTED":
                            print(f"\n!!! {clientname} accepted the invitation. Game starting... !!!\n")
                            print("-----------------------------------------------------------------------\n")
                            break
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
            # Wait for client to accept invitation
            response = self.client.recv(1024).decode()
            if response == "Request for IP and PORT":
                time.sleep(0.1)
                print("!!! Receive request for IP and PORT !!!\n")
                print("-----------------------------------------------------------------------\n")
                # Create game TCP server
                if (game_type == "1"):
                    self.Game_1_p1(GameIP, GamePort)
                elif (game_type == "2"):
                    self.Game_2_p1(GameIP, GamePort)
                
    def join_room(self):
        self.send_message(f"JOIN_ROOM")
        while True:
            room_name = input("Enter room name: ")
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
        GamePort = int(GamePort)
        if (GameType == "1"):
            self.Game_1_p2(GameIP, GamePort)
        elif (GameType == "2"):
            self.Game_2_p2(GameIP, GamePort)
                
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

    def logout(self):
        self.send_message(f"LOGOUT {self.username}")
        response = self.client.recv(1024).decode()
        print(f"LOGOUT MSG={response}")
        if response == "SUCCESS Logged out":
            print("\n!!! Logout successful !!!\n")
            print("-----------------------------------------------------------------------\n")
        else:
            print("\n!!! Logout failed. Please try again. !!!\n")
            print("-----------------------------------------------------------------------\n")

    def check_game_over(self, board, row, col, player):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # 右, 下, 右下斜, 左下斜
        for dr, dc in directions:
            count = 1  # 包括自己
            # 向一个方向检查
            for i in range(1, 5):
                r, c = row + dr * i, col + dc * i
                if 0 <= r < 15 and 0 <= c < 15 and board[r][c] == player:
                    count += 1
                else:
                    break
            # 向相反方向检查
            for i in range(1, 5):
                r, c = row - dr * i, col - dc * i
                if 0 <= r < 15 and 0 <= c < 15 and board[r][c] == player:
                    count += 1
                else:
                    break
            if count >= 5:
                return True
        return False
    
    def receive_invitation(self, msg):
        try:
            print(f"Received message: [{msg}]")
            if msg.startswith("Invited to"):
                room_name = msg.split()[2]
                print(f"\n!!! You have received an invitation to join [{room_name}] !!!")
                # Additional logic to accept or reject the invitation
                acc = input("Do you accept the invitation? (y/n): ").strip().lower()
                if acc == "y":
                    self.send_message("ACCEPT")
                    time.sleep(0.2)
                    self.send_message("ACCEPT")
                    time.sleep(0.2)
                    # self.send_message("ACCEPT")
                    # time.sleep(0.2)
                    # Proceed with any game-specific logic
                    TCPinfo = self.client.recv(1024).decode()
                    print(f"Received TCP info: {TCPinfo}")
                    GameIP, GamePort, Gametype = TCPinfo.split()
                    GamePort = int(GamePort)
                    time.sleep(0.5)
                    if (Gametype == "1"):
                        self.Game_1_p2(GameIP, GamePort)
                    elif (Gametype == "2"):
                        self.Game_2_p2(GameIP, GamePort)
                else:
                    self.send_message("REJECT")
        except Exception as e:
            print(f"Error while receiving invitation: {e}")
        finally:
            # 清空緩衝區
            self.clear_socket_buffer()

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
            


    def Game_1_p1(self, GameIP, GamePort, double=False):
        self.game_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.game_server.bind((GameIP, GamePort))
            self.game_server.listen(1)
            print(f"Game server created and listening on {GameIP}:{GamePort}\n")
            
            self.send_message(f"{GameIP} {GamePort}")
            time.sleep(0.2)
            self.game_server.settimeout(10)  # 設置超時時間為 5 秒
            try:
                conn, addr = self.game_server.accept()
                print("send twice")
                # self.send_message(f"{GameIP} {GamePort}")
                # time.sleep(0.2)
                print(f"Player connected from {addr}")
                self.send_message("START")
                time.sleep(0.1)
            except socket.timeout:
                print("No client connected within the timeout period. Exiting...")
                self.send_message("DISCONNECTED")
                time.sleep(0.2)
                self.send_message("DISCONNECTED")
                time.sleep(0.2)
                self.game_server.close()
                return  # 或者 exit() 結束程式

            board = [[' ' for _ in range(15)] for _ in range(15)]
            current_player = 'X'

            def print_board():
                print("\n  " + " ".join([str(i).rjust(2) for i in range(15)]))
                for idx, row in enumerate(board):
                    print(str(idx).rjust(2) + " " + " ".join(row))
                print("\n")

            print("Game Start! You are 'X'")
            conn.sendall("Game Start! You are 'O'\n".encode())

            game_over = False
            while not game_over:
                print_board()
                move = input("Enter your move (row,col) or quit (q): ")
                if move == 'q':
                    game_over = True
                    break
                try:
                    row, col = map(int, move.split(','))
                    if board[row][col] == ' ':
                        board[row][col] = current_player
                        conn.sendall(f"MOVE {row},{col}".encode())
                        if self.check_game_over(board, row, col, current_player):
                            print("You win!")
                            conn.sendall("GAME OVER - You lose".encode())
                            game_over = True
                        current_player = 'O'
                    else:
                        print("Invalid move, try again.")
                        continue
                except (ValueError, IndexError):
                    print("Invalid input. Please enter row,col.")
                    continue

                if not game_over:
                    print("Waiting for opponent's move...")
                    opponent_move = conn.recv(1024).decode()
                    if opponent_move.startswith("MOVE"):
                        _, move = opponent_move.split()
                        row, col = map(int, move.split(','))
                        board[row][col] = current_player
                        if self.check_game_over(board, row, col, current_player):
                            print("You lose!")
                            conn.sendall("GAME OVER - You win".encode())
                            game_over = True
                        current_player = 'X'

            print("\nGame Over!\n")
            print("-----------------------------------------------------------------------\n")
            
            conn.close()
            self.game_server.close()
            # if double:
            #     self.send_message("END")
            #     time.sleep(0.1)
            self.send_message("END")
            time.sleep(0.3)
            self.send_message("END")
            time.sleep(0.3)

        except socket.error as e:
            print(f"Error creating game server: {e}\n")
            self.game_server.close()

    def Game_1_p2(self, GameIP, GamePort):
        game_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"Connecting to game server at {GameIP}:{GamePort}")
            game_client.connect((GameIP, GamePort))
            print(f"Connected to game server at {GameIP}:{GamePort}")

            board = [[' ' for _ in range(15)] for _ in range(15)]
            current_player = 'O'

            def print_board():
                print("\n  " + " ".join([str(i).rjust(2) for i in range(15)]))
                for idx, row in enumerate(board):
                    print(str(idx).rjust(2) + " " + " ".join(row))
                print("\n")

            game_start_msg = game_client.recv(1024).decode()
            print(game_start_msg)

            game_over = False
            while not game_over:
                print("Waiting for opponent's move...")
                opponent_move = game_client.recv(1024).decode()
                if opponent_move.startswith("MOVE"):
                    _, move = opponent_move.split()
                    row, col = map(int, move.split(','))
                    board[row][col] = 'X'
                    if self.check_game_over(board, row, col, 'X'):
                        print("You lose!")
                        game_client.sendall("GAME OVER - You win".encode())
                        game_over = True

                if not game_over:
                    print_board()
                    move = input("Enter your move (row,col) or quit (q): ")
                    if move == 'q':
                        game_over = True
                        break
                    try:
                        row, col = map(int, move.split(','))
                        if board[row][col] == ' ':
                            board[row][col] = current_player
                            game_client.sendall(f"MOVE {row},{col}".encode())
                            if self.check_game_over(board, row, col, current_player):
                                print("You win!")
                                game_client.sendall("GAME OVER - You lose".encode())
                                game_over = True
                        else:
                            print("Invalid move, try again.")
                            continue
                    except (ValueError, IndexError):
                        print("Invalid input. Please enter row,col.")
                        continue
                    
            print("\nGame Over!\n")
            print("-----------------------------------------------------------------------\n")


            game_client.close()

        except socket.error as e:
            print(f"Error connecting to game server at {GameIP}:{GamePort}: {e}\n")
            game_client.close()
            print("-----------------------------------------------------------------------\n")     

    def Game_2_p1(self, GameIP, GamePort, double=False):
        self.game_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.game_server.bind((GameIP, GamePort))
            self.game_server.listen(1)
            print(f"Game server created and listening on {GameIP}:{GamePort}")
            
            self.send_message(f"{GameIP} {GamePort}")
            time.sleep(0.2)
            self.game_server.settimeout(10)  # 設置超時時間為 5 秒
            try:
                conn, addr = self.game_server.accept()
                print("send twice")
                # self.send_message(f"{GameIP} {GamePort}")
                # time.sleep(0.2)
                print(f"Player connected from {addr}")
                self.send_message("START")
                time.sleep(0.1)
            except socket.timeout:
                print("No client connected within the timeout period. Exiting...")
                self.send_message("DISCONNECTED")
                time.sleep(0.2)
                self.send_message("DISCONNECTED")
                time.sleep(0.2)
                self.game_server.close()
                return  # 或者 exit() 結束程式
            
            conn.sendall("Game Start! You are Player 1\n".encode())

            game_over = False
            board = [[' ' for _ in range(7)] for _ in range(6)]  # 四連棋的棋盤大小
            current_player = 'X'

            def print_board():
                print("\n  " + " ".join([str(i).rjust(2) for i in range(7)]))
                for idx, row in enumerate(board):
                    print(str(idx).rjust(2) + " " + " ".join(row))
                print("\n")

            def drop_piece(col, player):
                for row in reversed(range(6)):  # 自底向上尋找空格
                    if board[row][col] == ' ':
                        board[row][col] = player
                        return row
                return -1

            print("Game 2 (Four-in-a-Row) Start! You are Player X")
            while not game_over:
                print_board()
                move = input("Enter column (0-6) to drop your piece or quit (q): ")
                if move == 'q':
                    game_over = True
                    break
                try:
                    col = int(move)
                    if 0 <= col < 7:
                        row = drop_piece(col, current_player)
                        if row != -1:
                            conn.sendall(f"MOVE {row},{col}".encode())
                            if self.check_game_over(board, row, col, current_player, connect_four=True):
                                print("You win!")
                                conn.sendall("GAME OVER - You lose".encode())
                                game_over = True
                            current_player = 'O'  # Switch player
                        else:
                            print("Column is full, try another.")
                            continue
                    else:
                        print("Invalid column, try again.")
                        continue
                except ValueError:
                    print("Invalid input. Please enter a valid column number.")
                    continue

                if not game_over:
                    print("Waiting for opponent's move...")
                    opponent_move = conn.recv(1024).decode()
                    if opponent_move.startswith("MOVE"):
                        _, move = opponent_move.split()
                        row, col = map(int, move.split(','))
                        board[row][col] = current_player
                        if self.check_game_over(board, row, col, current_player, connect_four=True):
                            print("You lose!")
                            conn.sendall("GAME OVER - You win".encode())
                            game_over = True
                        current_player = 'X'  # Switch player

            print("\nGame Over!\n")
            print("-----------------------------------------------------------------------\n")

            conn.close()
            self.game_server.close()
            # if double:
            #     self.send_message("END")
            #     time.sleep(0.1)
            self.send_message("END")
            time.sleep(0.3)
            self.send_message("END")
            time.sleep(0.3)
            
        except socket.error as e:
            print(f"Error creating game server: {e}\n")
            self.game_server.close()

    def Game_2_p2(self, GameIP, GamePort):
        game_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"Connecting to game server at {GameIP}:{GamePort}")
            game_client.connect((GameIP, GamePort))
            print(f"Connected to game server at {GameIP}:{GamePort}")

            board = [[' ' for _ in range(7)] for _ in range(6)]
            current_player = 'O'

            def print_board():
                print("\n  " + " ".join([str(i).rjust(2) for i in range(7)]))
                for idx, row in enumerate(board):
                    print(str(idx).rjust(2) + " " + " ".join(row))
                print("\n")

            def drop_piece(col, player):
                for row in reversed(range(6)):
                    if board[row][col] == ' ':
                        board[row][col] = player
                        return row
                return -1

            game_start_msg = game_client.recv(1024).decode()
            print(game_start_msg)

            game_over = False
            while not game_over:
                print("Waiting for opponent's move...")
                opponent_move = game_client.recv(1024).decode()
                if opponent_move.startswith("MOVE"):
                    _, move = opponent_move.split()
                    row, col = map(int, move.split(','))
                    board[row][col] = 'X'
                    if self.check_game_over(board, row, col, 'X', connect_four=True):
                        print("You lose!")
                        game_client.sendall("GAME OVER - You win".encode())
                        game_over = True

                if not game_over:
                    print_board()
                    move = input("Enter column (0-6) to drop your piece or quit (q): ")
                    if move == 'q':
                        game_over = True
                        break
                    try:
                        col = int(move)
                        if 0 <= col < 7:
                            row = drop_piece(col, current_player)
                            if row != -1:
                                game_client.sendall(f"MOVE {row},{col}".encode())
                                if self.check_game_over(board, row, col, current_player, connect_four=True):
                                    print("You win!")
                                    game_client.sendall("GAME OVER - You lose".encode())
                                    game_over = True
                            else:
                                print("Column is full, try another.")
                                continue
                        else:
                            print("Invalid column, try again.")
                            continue
                    except ValueError:
                        print("Invalid input. Please enter a valid column number.")
                        continue

            print("\nGame Over!\n")
            print("-----------------------------------------------------------------------\n")

            game_client.close()
            
        except socket.error as e:
            print(f"Error connecting to game server at {GameIP}:{GamePort}: {e}\n")
            game_client.close()
            print("-----------------------------------------------------------------------\n")


if __name__ == "__main__":
    player = GamePlayer()
    login = False
    while True:

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
        cmd = input("Enter number: ")

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
                player.client.settimeout(0.1)  # Set timeout to 1 second for this operation
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                # print(f"Received interrupt message: {msg}")
                if msg.startswith("Invited to"):
                    player.receive_invitation(msg)  # Handle the message if received
                    continue
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
            player.logout()
            login = False
        # List rooms
        elif login and cmd == "2":
            try:
                player.client.settimeout(0.1)  # 設置超時時間
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                if msg.startswith("Invited to"):
                    player.receive_invitation(msg)  # 處理收到的邀請
                    continue
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
                player.client.settimeout(0.1)  # Set timeout to 1 second for this operation
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                # print(f"Received interrupt message: {msg}")
                if msg.startswith("Invited to"):
                    player.receive_invitation(msg)  # Handle the message if received
                    continue
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
            player.create_room()
        # Join room
        elif login and cmd == "4":
            try:
                player.client.settimeout(0.1)  # Set timeout to 1 second for this operation
                msg = player.client.recv(1024).decode()
                player.client.settimeout(None)
                # print(f"Received interrupt message: {msg}")
                if msg.startswith("Invited to"):
                    player.receive_invitation(msg)  # Handle the message if received
                    continue
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
            player.join_room()
        else:
            print("Invalid command")
            continue
