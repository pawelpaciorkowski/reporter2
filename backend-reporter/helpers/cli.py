import progressbar

def pb_iterate(sequence):
    pb = progressbar.ProgressBar(maxval=100)
    total = len(sequence)
    pb.start()
    for i, elem in enumerate(sequence):
        pb.update(i * 100 / total)
        yield elem
    pb.finish()
