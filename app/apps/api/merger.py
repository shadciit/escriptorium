from collections import Counter
from math import sqrt
import sys
from telnetlib import SE
from typing import List, Sequence, Tuple
from api.serializers import DetailedLineSerializer

from core.models import Line
from munkres import Munkres, Matrix, AnyNum

def _distance(a: Line, b: Line) -> float:
    pt1 = a.baseline[-1]
    pt2 = b.baseline[0]
    dist = sqrt((pt2[1] - pt1[1])**2 + (pt2[0] - pt1[0])**2)

    return dist


def _build_dist_matrix(lines: List[Line]) -> List[List[float]]:
    # The distance matrix contains the distance between every two lines
    # mat[i][j] is the distance from the end of lines[i] to the beginning of lines[j]
    #
    # We add two extra dummy lines, at len(lines) and len(lines) + 1. 
    # The first dummy line at len(lines) signifies the start of the sequence. Its distance to any other
    # line is 1, and the distance from any line to it is maxsize.
    # The second dummy line, at len(lines) + 1 signifies the end of the sequence. Its distance to any other line
    # is maxsize, and from any line to it is 1.

    dist_matrix: List[List[float]] = []
    for i in range(len(lines)):
        line_dist = [_distance(lines[i], lines[j]) if i!=j else sys.maxsize for j in range(len(lines))]
        line_dist += [sys.maxsize, 1]
        dist_matrix.append(line_dist)
    dist_matrix.append([1.0] * len(lines) + [sys.maxsize, sys.maxsize])
    dist_matrix.append([sys.maxsize] * (len(lines) + 2))

    return dist_matrix

def _find_order(lines: List[Line]):
    mat = _build_dist_matrix(lines)
    m = Munkres()
    indices = m.compute(mat)  # type:ignore - For some reason List[List[float]] is detected as a Matrix, even though it really is
    # indices contain the sequence in a way that index[x][1] is the line after line x, and index[x][0] is just x.
    # We start with index[len(lines)][1] which contains the first line
    # The line for which index[l][1] == len(lines) + 1 is the last line
    next_index = [index[1] for index in indices]
    order: List[int] = []

    cur = len(lines) # The node at len(lines) is before the first line
    while next_index[cur] != len(lines) + 1: # The node at len(lines) + 1 is after the last line 
        order.append(next_index[cur])
        cur = next_index[cur]

    return order

def _merge_baseline(lines: List[Line], order: List[int]) -> List[Tuple[int, int]]:
    baseline = []
    for idx in order:
        baseline += lines[idx].baseline
    return baseline

def _find_typology(lines):
    types = [line.typology for line in lines]
    ctr = Counter(types)
    common = ctr.most_common(2)

    if len(common) == 1 or common[1][1] < common[0][1]:
        return common[0][0]
        
    return lines[0].typology  # If there is no majority, return the typology of the first line

def merge_lines(lines: List[Line]):
    order = _find_order(lines)

    # We don't really create the line, just the JSON that will allow the serializers to create the line.
    # This guarantees that all the error checks, validations and dependent async processes (calculating the mask, for example)
    # run as usual.

    serializer = DetailedLineSerializer(lines[0], many=False)
    merged_json = serializer.data

    # Clear fields we don't need
    unnecessary = ('pk', 'external_id', 'region',)
    for key in unnecessary:
        del(merged_json[key])

    merged_json['baseline'] = _merge_baseline(lines, order)
    merged_json['typology'] = _find_typology(lines)

    # TODO: merge transcriptions
    return merged_json