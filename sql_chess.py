from flask import Flask, request, jsonify
import chess
import uuid
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)


games = {}

piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9
}

def alpha_beta_pruning(board, depth, alpha, beta, maximizing_player):
    if depth == 0 or board.is_game_over():
        return None, evaluate_board(board)

    if maximizing_player:
        max_eval = float('-inf')
        best_move = None
        for move in board.legal_moves:
            board.push(move)
            eval = alpha_beta_pruning(board, depth-1, alpha, beta, False)[1]
            board.pop()
            if eval > max_eval:
                max_eval = eval
                best_move = move
            alpha = max(alpha, eval)
            if alpha >= beta:
                break
        return best_move, max_eval

    else:
        min_eval = float('inf')
        best_move = None
        for move in board.legal_moves:
            board.push(move)
            eval = alpha_beta_pruning(board, depth-1, alpha, beta, True)[1]
            board.pop()
            if eval < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eval)
            if alpha >= beta:
                break
        return best_move, min_eval

def evaluate_board(board):
    material_balance = 0
    for piece_type in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        material_balance += (len(board.pieces(piece_type, chess.WHITE)) - len(board.pieces(piece_type, chess.BLACK))) * piece_values[piece_type]
    return material_balance

@app.route('/start_game', methods=['POST'])
def start_game():
    game_type = request.json.get('type', 'ai')
    if game_type not in ['ai']:
        return jsonify({'error': 'Invalid game type'})

    game_id = request.json.get('game_id', str(uuid.uuid4()))
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Sai481309@',
        database='chess'
    )
    cursor = conn.cursor()

    if game_id in games:
        return jsonify({'error': 'Game already in progress'})

    color = request.json.get('color')
    if color not in ['white', 'black']:
        return jsonify({'error': 'Invalid color'})

    depth = request.json.get('depth', 3)
    if not isinstance(depth, int) or depth < 1:
        return jsonify({'error': 'Invalid depth value'})

    if depth > 10:
        return jsonify({'error': 'Depth cannot be greater than 10'})

    board = chess.Board()
    if game_type == 'ai':
        human_color = chess.WHITE if color == 'white' else chess.BLACK
        ai_color = not human_color
        if ai_color == chess.WHITE:
            ai_move, _ = alpha_beta_pruning(board, depth=depth, alpha=float('-inf'), beta=float('inf'), maximizing_player=True)
        else:
            ai_move = None
        sql = "INSERT INTO games (id, board, type, human_color, ai_color, depth, ended) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (game_id, str(board.fen()), game_type, int(human_color), int(ai_color), depth, 0)
    else:
        sql = "INSERT INTO games (id, board, type, ended) VALUES (%s, %s, %s, %s)"
        values = (game_id, str(board.fen()), game_type, 0)

    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'game_id': game_id, 'board': str(board.fen()), 'result': '*', 'ai_move': str(ai_move) if ai_move else None})


@app.route('/make_move', methods=['POST'])
def make_move():
    game_id = request.json.get('game_id')
    if not game_id:
        return jsonify({'error': 'Invalid game ID'})

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Sai481309@',
        database='chess'
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM games WHERE id=%s', (game_id,))
    game_data = cursor.fetchone()

    if not game_data:
        return jsonify({'error': 'Invalid game ID'})

    board = chess.Board(game_data['board'])
    human_color = game_data['human_color']
    ai_color = game_data['ai_color']
    ended = game_data['ended']

    if ended:
        return jsonify({'error': 'Game has ended'})

    if human_color == ai_color:
        return jsonify({'error': 'Invalid game type'})

    if ai_color is not None and ai_color == board.turn:
        # AI's turn
        depth = int(request.json.get('depth', 3))
        ai_move, _ = alpha_beta_pruning(board, depth=depth, alpha=float('-inf'), beta=float('inf'), maximizing_player=True)
        board.push(ai_move)
        result = get_game_result(board)

        cursor.execute('UPDATE games SET board=%s, ended=%s WHERE id=%s', (board.fen(), result != '*', game_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'game_id': game_id, 'board': str(board.fen()), 'result': result, 'ai_move': str(ai_move)})
    else:
        # Player's turn
        player_move_str = request.json.get('move')
        if not player_move_str:
            return jsonify({'error': 'Invalid move'})

        player_move = chess.Move.from_uci(player_move_str)
        if player_move not in board.legal_moves:
            return jsonify({'error': 'Invalid move'})

        board.push(player_move)
        result = get_game_result(board)

        cursor.execute('UPDATE games SET board=%s, ended=%s WHERE id=%s', (board.fen(), result != '*', game_id))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'game_id': game_id, 'board': str(board.fen()), 'result': result})

@app.route('/game_state', methods=['GET'])
def game_state():
    game_id = request.args.get('game_id')
    if not game_id:
        return jsonify({'error': 'Invalid game ID'})

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Sai481309@',
        database='chess'
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT board FROM games WHERE id=%s', (game_id,))
    game_data = cursor.fetchone()

    if not game_data:
        return jsonify({'error': 'Invalid game ID'})

    board_state = game_data['board']
    result = get_game_result(chess.Board(board_state))

    cursor.close()
    conn.close()

    return jsonify({'game_id': game_id, 'board': board_state, 'result': result})

@app.route('/end_game', methods=['POST'])
def end_game():
    game_id = request.json.get('game_id')
    if not game_id:
        return jsonify({'error': 'Invalid game ID'})

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Sai481309@',
        database='chess'
    )
    cursor = conn.cursor()
    cursor.execute('UPDATE games SET board=%s, ended=%s WHERE id=%s', (chess.Board().fen(), 1, game_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Game ended and board reset'})

def get_game_result(board):
    result = board.result()
    if result == '1-0':
        return 'white'
    elif result == '0-1':
        return 'black'
    elif result == '1/2-1/2':
        return 'draw'
    else:
        return '*'
    
if __name__ == '__main__':
    app.run()