import chess
import random

def play_game():
    board = chess.Board()

    # Prompt players for names and piece choices
    player1_name = input("Enter name for player 1: ")
    player2_name = input("Enter name for player 2: ")
    white_player_name = input("Which player wants to play as White? (1 or 2): ")
    if white_player_name == '1':
        white_piece = 'K'
        black_piece = 'k'
    else:
        white_piece = 'k'
        black_piece = 'K'
    board.set_piece_at(chess.parse_square('e1'), chess.Piece.from_symbol(white_piece))
    board.set_piece_at(chess.parse_square('e8'), chess.Piece.from_symbol(black_piece))

    while not board.is_game_over():
        print(board)
        move = get_player_move(board, player1_name, player2_name)
        board.push(move)

    print(board)
    print("Game over! Result: ", board.result())

def get_player_move(board, player1_name, player2_name):
    while True:
        try:
            uci = input(f"{player1_name}, enter your move in UCI format (e.g. e2e4): ")
            move = chess.Move.from_uci(uci)
            if move in board.legal_moves:
                return move
            else:
                print("Illegal move, please try again.")
        except ValueError:
            print("Invalid move format, please try again.")

        try:
            uci = input(f"{player2_name}, enter your move in UCI format (e.g. e7e5): ")
            move = chess.Move.from_uci(uci)
            if move in board.legal_moves:
                return move
            else:
                print("Illegal move, please try again.")
        except ValueError:
            print("Invalid move format, please try again.")




if __name__ == '__main__':
    play_game()