import socket
import sys

def start_game(is_host, game_ip, game_port):
    board = [[' ' for _ in range(15)] for _ in range(15)]
    current_player = 'X' if is_host else 'O'
    opponent = 'O' if is_host else 'X'
    conn = None

    def print_board():
        print("\n  " + " ".join([str(i).rjust(2) for i in range(15)]))
        for idx, row in enumerate(board):
            print(str(idx).rjust(2) + " " + " ".join(row))
        print("\n")

    def check_game_over(row, col, player):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # right, down, right-down diagonal, left-down diagonal
        for dr, dc in directions:
            count = 1
            for i in range(1, 5):
                r, c = row + dr * i, col + dc * i
                if 0 <= r < 15 and 0 <= c < 15 and board[r][c] == player:
                    count += 1
                else:
                    break
            for i in range(1, 5):
                r, c = row - dr * i, col - dc * i
                if 0 <= r < 15 and 0 <= c < 15 and board[r][c] == player:
                    count += 1
                else:
                    break
            if count >= 5:
                return True
        return False

    if is_host:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((game_ip, game_port))
        server.listen(1)
        server.settimeout(5)  # 設定超時時間為 5 秒
        print(f"Hosting Gomoku on {game_ip}:{game_port}")

        try:
            conn, addr = server.accept()
            print(f"Player connected from {addr}")
        except socket.timeout:
            print("Timeout: No player connected within 5 seconds.")
            server.close()  # 關閉伺服器以釋放資源
            return

    else:
        print(f"Connecting to game host at {game_ip}:{game_port}")
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((game_ip, game_port))
        print(f"Connected to game host at {game_ip}:{game_port}")

    game_over = False
    print(f"Game started! You are '{current_player}'")
    if not is_host:
        print("Waiting for the host's move...")

    while not game_over:
        if is_host or current_player == 'O':
            print_board()
            move = input("Enter your move (row,col) or quit (q): ")
            if move == 'q':
                conn.sendall("QUIT".encode())
                break
            try:
                row, col = map(int, move.split(','))
                if board[row][col] == ' ':
                    board[row][col] = current_player
                    conn.sendall(f"MOVE {row},{col}".encode())
                    if check_game_over(row, col, current_player):
                        print("You win!")
                        conn.sendall("GAME_OVER".encode())
                        game_over = True
                else:
                    print("Invalid move, try again.")
                    continue
            except ValueError:
                print("Invalid input. Use 'row,col' format.")
                continue

        if not game_over:
            opponent_move = conn.recv(1024).decode()
            if opponent_move.startswith("MOVE"):
                _, move = opponent_move.split()
                row, col = map(int, move.split(','))
                board[row][col] = opponent
                if check_game_over(row, col, opponent):
                    print_board()
                    print("You lose!")
                    conn.sendall("GAME_OVER".encode())
                    game_over = True
            elif opponent_move == "QUIT":
                print("Opponent quit the game.")
                game_over = True

    conn.close()
    if is_host:
        server.close()
    print("Game over!")



def main():
    if len(sys.argv) != 4:
        print("Usage: python Gomoku.py <is_host> <game_ip> <game_port>")
        sys.exit(1)

    is_host = sys.argv[1] == "1"  # 主機標記
    game_ip = sys.argv[2]         # 遊戲 IP
    game_port = int(sys.argv[3])  # 遊戲端口

    start_game(is_host, game_ip, game_port)

if __name__ == "__main__":
    print("--------------------------Gomoku Game-------------------------------")
    main()
