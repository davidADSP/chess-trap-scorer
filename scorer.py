import io
import argparse

import chess.pgn

from node import Node

class TrapScorer():
    def __init__(self, pgn):
        self.pgn = pgn
        self._calculate_score()

    def _calculate_score(self):
        
        try:
            game = chess.pgn.read_game(io.StringIO(self.pgn))
        except:
            raise Exception(f'Invalid PGN {self.pgn}')

        board = game.board()
        moves = list(game.mainline_moves())
        
        if len(moves) % 2 == 0:
            perspective = chess.WHITE
            self.perspective_str = 'White'
        else:
            perspective = chess.BLACK
            self.perspective_str = 'Black'

        self.likelihood = 1
        self.previous_potency = 0.5
        self.likelihood_path = []

        for move in moves:
            node = Node(board.fen())

            if board.turn == perspective:
                _, _, self.previous_potency, _, _ = node.score_moves()
            else:
                move_stats, chance = node.find_move(move)
                self.likelihood *= chance
                self.likelihood_path.append((move_stats['san'], chance))
                
            board.push(move)

        # Calculate potency
        self.node = Node(board.fen(), lastmove = move)
        _, self.best_move, self.potency, self.potency_range, self.total_games = self.node.score_moves()
        
        self.shock = self.potency - self.previous_potency
        
        self.av_likelihood = pow(self.likelihood , (1/len(self.likelihood_path)))
        
        self.score = self.av_likelihood * self.potency
        
        self.frequency = int(1 / self.likelihood)
        
        

    def print_output(self):

        self.node.show()
        print(f"{self.perspective_str} to play")
        print("Total moves:\t",len(self.likelihood_path))
        for move, chance in self.likelihood_path:
            print(f'\t{move}:\t', "{:.2%}".format(chance))
        print("Likelihood:\t","{:.2%}".format(self.likelihood))
        print("Frequency:\t",f"Every {self.frequency} games")
        print("Av Move Prob:\t","{:.2%}".format(self.av_likelihood))
        print()
        print("Continuation:\t",self.best_move)
        print("Total games:\t", self.total_games)
        print("Shock:\t\t", "{:+.2%}".format(self.shock), "({:.2%}".format(self.previous_potency), "->", "{:.2%})".format(self.potency))
        print("Potency:\t", "{:.2%}".format(self.potency), 'CI', ["{:.2%}".format(x) for x in self.potency_range], "(95%)")
        print()
        print(f"Trap Score:\t","{:.2%}".format(self.score), "( =", "{:.2%}".format(self.av_likelihood), "*", "{:.2%}".format(self.potency), ")")


def main(args):
    scorer = TrapScorer(args.pgn)
    scorer.print_output()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=('Score a Trap'))
    parser.add_argument('--pgn', '-p', type=str, help='PGN of the position just after the opponent has fallen into the trap')
    args = parser.parse_args()
    main(args)
