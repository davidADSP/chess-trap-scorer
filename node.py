import chess.svg
import requests
import scipy.stats as st
import numpy as np
import time

import config 

def calc_percs(white, black, draws):

    n = white + black + draws

    if n > 0:
        total_games = n
        white_perc = white / n
        black_perc = black / n
        draw_perc = draws / n
        return white_perc, black_perc, draw_perc, total_games
    else:
        return None, None, None, 0

    
def calc_value(p, n):
    if n > 5:
        lb_value = max(0, p - st.norm.ppf(1 - config.ALPHA/2) * np.sqrt(p * (1-p) / n))
        ub_value = max(0, p + st.norm.ppf(1 - config.ALPHA/2) * np.sqrt(p * (1-p) / n))
    else:
        p = 0
        lb_value = 0
        ub_value = 0

    return p, lb_value, ub_value, n


class Node():
    def __init__(self, fen, lastmove = '', san = '', ):
        self.fen = fen
        self.short_fen = fen[:-4]
        self.lastmove = lastmove
        self.san = san
        self.terminal = '#' in san
        self.explored = False
        self.best_move = None
        
        self.board = chess.Board(fen)
        
        self.stats = self.call_api()
        self.parse_stats()
           
    def show(self):
        try:
            print('')
            display(chess.svg.board(self.board, lastmove = self.lastmove, size = 400))
            print('')
        except:
            pass

    def play(self, san):
        board = chess.Board(self.fen)
        move = board.push_san(san)
        node = Node(board.fen(), lastmove = move, san = san)
        return node
       
               
    def call_api(self):
        variant = config.VARIANT
        speeds = config.SPEEDS
        ratings = config.RATINGS
        moves = config.MOVES
        recentGames = 0
        topGames = 0
        play = ""
        
        url = 'https://explorer.lichess.ovh/lichess?'
        url += f'variant={variant}&'
        for speed in speeds:
            url += f'speeds[]={speed}&'

        for rating in ratings:
            url += f'ratings[]={rating}&'

        url += f'recentGames={recentGames}&'
        url += f'topGames={topGames}&'
        url += f'moves={moves}&'
        url += f'play={play}&'
        url += f'fen={self.fen}'
        
        self.opening_url = url
        
        while True:
            r = requests.get(url)
            if r.status_code == 429:
                print('Rate limited - waiting 10s...')
                time.sleep(10)
            else:
                response = r.json()
                break

        return response



    def parse_stats(self, move = None):

        stats = self.stats
        stats['white_perc'], stats['black_perc'], stats['draw_perc'], stats['total_games'] = calc_percs(stats['white'], stats['black'], stats['draws'])

        for m in self.stats['moves']:
            m['white_perc'], m['black_perc'], m['draw_perc'], m['total_games'] = calc_percs(m['white'], m['black'], m['draws'])



    def score_moves(self):

        moves = {}
        best_lb_value = -np.inf
        best_move = None
        for move in self.stats['moves']:
            if self.board.turn == chess.WHITE:
                value, lb_value, ub_value, n = calc_value(move['white_perc'], move['total_games'])
            else:
                value, lb_value, ub_value, n = calc_value(move['black_perc'], move['total_games'])

            key = move['san']
            moves[key] = {
                'value': value
                , 'lb_value': lb_value
                , 'ub_value': ub_value
                , 'n': n
            }

        lb_potencies = {k:v['lb_value'] for k,v in moves.items()}
        best_move = max(lb_potencies, key=lb_potencies.get)

        potency = moves[best_move]['value']
        lb_potency = moves[best_move]['lb_value']
        ub_potency = moves[best_move]['ub_value']
        n = moves[best_move]['n']
        
        return moves, best_move, potency, (lb_potency, ub_potency), n

    def find_move(self, move):
        try: # Try to find the next move in the opening stats from the API
            if move.uci() == 'e8g8':
                move_uci = 'e8h8'
            elif move.uci() == 'e1g1':
                move_uci = 'e1h1'
            elif move.uci() == 'e8c8':
                move_uci = 'e8a8'
            elif move.uci() == 'e1c1':
                move_uci = 'e1a1'
            else:
                move_uci = move.uci()

            move_stats = next(item for item in self.stats['moves'] if item["uci"] == move_uci)
        except:
            raise Exception(f'Cannot find move {move_uci} in opening explorer API response') 

        chance = move_stats['total_games'] / self.stats['total_games']

        return move_stats, chance

    def create_children(self):

        children = []
        for i, m in enumerate(self.stats['moves']):
            node = self.play(m['san'])
            children.append(node)
        return children
        
