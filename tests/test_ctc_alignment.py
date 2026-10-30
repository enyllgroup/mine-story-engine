import numpy as np
import pytest
from minestory.ctc_alignment import ctc_viterbi, make_labels


def test_ctc_alignment_requires_blank_between_repeated_symbols():
    # CTC: a, blank, a, blank, b -- two separate a's, not one held note.
    logits=np.full((5,3),-10.0)
    for i,symbol in enumerate([1,0,1,0,2]):logits[i,symbol]=10.0
    spans=ctc_viterbi(logits,[1,1,2])
    assert [(start,end) for start,end,_ in spans]==[(0,1),(2,3),(4,5)]
    assert min(score for _,_,score in spans)>.99


def test_alignment_does_not_invent_pronunciation_of_unsupported_numbers():
    vocab={'<pad>':0,'|':1,**{c:i+2 for i,c in enumerate('seis')}}
    labels,owners=make_labels(['6'],vocab)
    assert labels==[vocab[c] for c in 'seis'] and owners==[0]*4
    with pytest.raises(ValueError,match='Unsupported word'):
        make_labels(['75'],vocab)
