from math import sqrt
from typing import List

from core.models import Line


def _distance(a: Line, b: Line) -> float:
    pt1 = a.baseline[-1]
    pt2 = b.baseline[0]
    dist = sqrt((pt2[1] - pt1[1])**2 + (pt2[0] - pt1[0])**2)

    return dist


def _build_dist_matrix(lines: List[Line]):
    # dist_matrix[i][j] is the distance from end of lines[i] to start of lines[j]
    # We do not use list comprehension because double list comprehension is not so readable
    dist_matrix: List[List[float]] = []
    for i in range(len(lines)):
        line_dist = [_distance(lines[i], lines[j]) for j in range(len(lines))]
        dist_matrix.append(line_dist)

    return dist_matrix

def _find_order(lines: List[Line]):
    mat = _build_dist_matrix(lines)
    m = Munkres()


def merge_lines(lines: List[Line]):
    order = find_order(lines)