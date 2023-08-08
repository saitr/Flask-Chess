from flask import Flask, request, jsonify
import chess
import uuid
from flask_cors import CORS

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
    if game_type not in ['ai', 'player']:
        return jsonify({'error': 'Invalid game type'})

    if 'game_id' in request.json:
        game_id = request.json['game_id']
        if game_id in games:
            return jsonify({'error': 'Game already in progress'})
    else:
        return jsonify({'error': 'Missing game ID'})

    if 'color' in request.json:
        color = request.json['color']
        if color not in ['white', 'black']:
            return jsonify({'error': 'Invalid color'})
    else:
        return jsonify({'error': 'Missing color'})

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
        games[game_id] = {'board': board, 'type': game_type, 'human_color': human_color, 'ai_color': ai_color, 'ended': False}
    else:
        games[game_id] = {'board': board, 'type': game_type, 'ended': False}

    return jsonify({'game_id': game_id, 'board': str(board.fen()), 'result': '*', 'ai_move': str(ai_move) if ai_move else None})

@app.route('/make_move', methods=['POST'])
def make_move():
    game_id = request.json.get('game_id')
    print(game_id)
    if game_id not in games:
        print(game_id)
        return jsonify({'error': 'Invalid game ID'})

    board = games[game_id]['board']
    human_color = games[game_id]['human_color']
    ai_color = games[game_id].get('ai_color')
    ended = games[game_id]['ended']

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
        games[game_id]['board'] = board
        games[game_id]['ended'] = result != '*'
        return jsonify({'game_id': game_id, 'board': str(board.fen()), 'result': result, 'ai_move': str(ai_move)})
    else:
        # Player's turn
        player_move_str = request.json.get('move')
        if player_move_str is None:
            return jsonify({'error': 'Invalid move'})

       


        player_move = chess.Move.from_uci(player_move_str)
        if player_move not in board.legal_moves:
            return jsonify({'error': 'Invalid move'})

        board.push(player_move)
        result = get_game_result(board)
        games[game_id]['board'] = board
        games[game_id]['ended'] = result != '*'
        return jsonify({'game_id': game_id, 'board': str(board.fen()), 'result': result})

@app.route('/game_state', methods=['GET'])
def game_state():
    game_id = request.args.get('game_id')
    game = games.get(game_id)
    if game is None:
        return jsonify({'error': 'Game not found'})

    board_state = game['board'].fen()
    result = game['board'].result()
    return jsonify({'game_id': game_id, 'board': board_state, 'result': result})

@app.route('/end_game', methods=['POST'])
def end_game():
    game_id = request.json.get('game_id')
    if game_id not in games:
        return jsonify({'error': 'Game not found'})

    games[game_id]['board'] = chess.Board()
    games[game_id]['ended'] = True
    del games[game_id]  # delete game ID from games dictionary

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
    
@app.route('/new_game_pvp', methods=['POST'])
def new_game():
    data = request.get_json()
    player1_name = data.get('player1_name')
    player2_name = data.get('player2_name')
    white_player_name = data.get('white_player_name')

    if not all([player1_name, player2_name, white_player_name]):
        return jsonify({'error': 'Missing required fields'}), 400

    board = chess.Board()
    if white_player_name == '1':
        white_piece = 'K'
        black_piece = 'k'
    else:
        white_piece = 'k'
        black_piece = 'K'
    board.set_piece_at(chess.parse_square('e1'), chess.Piece.from_symbol(white_piece))
    board.set_piece_at(chess.parse_square('e8'), chess.Piece.from_symbol(black_piece))

    game_state = {
        'fen': board.fen(),
        'player1_name': player1_name,
        'player2_name': player2_name,
        'current_player': 1 if white_player_name == '1' else 2
    }

    return jsonify(game_state)

@app.route('/make_move_pvp', methods=['POST'])
def make_move_pvp():
    data = request.get_json()
    fen = data['board']
    move_str = data['move']

    board = chess.Board(fen)
    move = chess.Move.from_uci(move_str)
    if move in board.legal_moves:
        board.push(move)

    game_state = {
        'board': board.fen(),
        'current_player': 2 if board.turn else 1
    }

    return jsonify(game_state)

if __name__ == '__main__':
    app.run()
