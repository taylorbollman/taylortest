from functools import lru_cache

from .node import Node

try:
    from ..minichess.chess.fastchess_utils import prior_math
except ImportError:
    from minichess.chess.fastchess_utils import prior_math

import numpy as np


class MonteCarlo:

    def __init__(self, root_node: Node, all_moves, move_cap, dims, prior_noise_coefficient, cpuct, net=None):
        self.root_node = root_node
        self.move_cap = move_cap
        self.net = net
        self.all_moves = all_moves
        self.cnoise = prior_noise_coefficient
        self.cpuct = cpuct
        self.dims = dims

    def distribution(self):
        return self.root_node.child_number_visits

    def move_root(self, node, cut_parent=True):
        self.root_node = node
        if cut_parent:
            self.root_node.parent = None

    def make_choice(self, ply_count):
        best_move = self.root_node.get_move_to_make_for_search(ply_count)
        if best_move not in self.root_node.children:
            self.root_node.add_child(best_move, self.root_node.child_priors[best_move])
        return self.root_node.children[best_move]

    def simulate(self):
        leaf = self.root_node.select_leaf()
        # If the leaf is a terminal node, just return the actual result
        if leaf.state.game_result() is not None:
            leaf.update_win_value(leaf.state.game_result())
            return

        # The probability of going to each child-node, in addition to a value_estimate of the current one
        child_priors, value_estimate = self.net.predict(leaf.state.agent_board_state())

        # The neural net is set to predict positively if the person whose turn it is has a good position.
        # 1 means winning for person to play, -1 means losing
        # The search, however, is set up so that -1 is good for black, and 1 is good for white, regardless of who's playing
        # So if the neural net predicts 1 and it's black's turn, this means that it thinks that black is winning, but the search
        # will agree if it is given -1.
        child_priors = prior_math(leaf.illegal_moves_mask, self.dims, child_priors, self.move_cap, self.cnoise, value_estimate, leaf.player_number)
        leaf.expand(child_priors)
        leaf.update_win_value(value_estimate)