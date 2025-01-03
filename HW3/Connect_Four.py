import socket
import sys

def start_game(is_host, game_ip, game_port):
    board = [[' ' for _ in range(7)] for _ in range(6)]
    current_player = 'X' if is_host else 'O'
    opponent = 'O' if is_host else 'X'
    conn = None

    def print_board():
        print("\n  " + " ".join([str(i) for i in range(7)]))
        for row in board:
            print("  " + " ".join(row))
        print("\n")

    def drop_piece(col, player):
        for row in reversed(range(6)):
            if board[row][col] == ' ':
                board[row][col] = player
                return row
        return -1

    def check_game_over(row, col, player):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for i in range(1, 4):
                r, c = row + dr * i, col + dc * i
                if 0 <= r < 6 and 0 <= c < 7 and board[r][c] == player:
                    count += 1
                else:
                    break
            for i in range(1, 4):
                r, c = row - dr * i, col - dc * i
                if 0 <= r < 6 and 0 <= c < 7 and board[r][c] == player:
                    count += 1
                else:
                    break
            if count >= 4:
                return True
        return False

    if is_host:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((game_ip, game_port))
        server.listen(1)
        print(f"Hosting Connect Four on {game_ip}:{game_port}")
        conn, addr = server.accept()
        print(f"Player connected from {addr}")
    else:
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
            move = input("Enter column (0-6) or quit (q): ")
            if move == 'q':
                conn.sendall("QUIT".encode())
                break
            try:
                col = int(move)
                if 0 <= col < 7:
                    row = drop_piece(col, current_player)
                    if row != -1:
                        conn.sendall(f"MOVE {row},{col}".encode())
                        if check_game_over(row, col, current_player):
                            print("You win!")
                            conn.sendall("GAME_OVER".encode())
                            game_over = True
                    else:
                        print("Column is full, try again.")
                        continue
                else:
                    print("Invalid column, try again.")
                    continue
            except ValueError:
                print("Invalid input. Use a number between 0-6.")
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
    main()
