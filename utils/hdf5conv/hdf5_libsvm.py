import numpy, h5py, os
from scipy.sparse import csc_matrix
import config

class LIBSVM2HDF5():
    """Convert a file from LibSVM to HDF5."""

    def __init__(self, *args, **kwargs):
        self.offset_labels = []
        self.none = []


    def _explode_labels(self, label):
        label = numpy.double(''.join(label).split(','))
        ll = []
        if len(label) > 1:
            for l in label:
                ll.append([l, 1])
            self.offset_labels.append(int(max(label)))
        else:
            ll.append([0, label[0]])
            self.offset_labels.append(0)
        return ll


    def _parse_line(self, line):
        need_label = True
        need_idx = False
        need_val = False
        in_val = False
        idx = []
        val = []
        label = []
        attributes = []
        offset = 0
        for c in line:
            if need_label:
                if c.isspace():
                    need_label = False
                    need_idx = True
                    attributes.extend(self._explode_labels(label))
                else:
                    label.append(c)
            elif need_idx:
                if c == ':':
                    need_idx = False
                    need_val = True
                elif not c.isspace():
                    idx.append(c)
            elif need_val:
                if not c.isspace():
                    in_val = True
                    val.append(c)
                elif in_val:
                    in_val = False
                    need_val = False
                    need_idx = True
                    attributes.append([int(''.join(idx)) + self.offset_labels[-1], ''.join(val)])
                    idx = []
                    val = []

        return attributes


    def get_matrix(self, fname):
        """Retrieves a SciPy Compressed Sparse Column matrix from file.

        @param fname: filename to retrieve matrix from
        @type fname: string
        @return: compressed sparse column matrix
        @rtype: scipy.sparse.csc_matrix
        """
        indices = []
        indptr = [0]
        data = []
        ptr = 0
        infile = open(fname, 'r')
        for line in infile:
            attributes = self._parse_line(line)
            for a in attributes:
                indices.append(int(a[0]))
                data.append(numpy.double(a[1]))
                ptr += 1
            indptr.append(ptr)
        infile.close()

        return csc_matrix((numpy.array(data), numpy.array(indices), numpy.array(indptr)))


    def run(self, in_fname, out_fname):
        """Run the actual conversion process."""
        self.offset_labels = []
        A = self.get_matrix(in_fname)
        h = h5py.File(out_fname, 'w')

        if A.nnz/numpy.double(A.shape[0]*A.shape[1]) < 0.5: # sparse
            h.create_dataset('attributes_indices', data=A.indices, compression=config.COMPRESSION)
            h.create_dataset('attributes_indptr', data=A.indptr, compression=config.COMPRESSION)
            h.create_dataset('attributes_data', data=A.data, compression=config.COMPRESSION)
            h.attrs['comment'] = 'libsvm sparse'
        else: # dense
            A = A.todense().T
            h.create_dataset('attributes', data=A, compression=config.COMPRESSION)
            h.attrs['comment'] = 'libsvm dense'

        attribute_names = ['dim 1', '...', 'dim ' + str(A.shape[1])]
        h.create_dataset('attribute_names', data=attribute_names, compression=config.COMPRESSION)

        # without str(), h5py might barf
        h.attrs['name'] = str(os.path.basename(out_fname).split('.')[0])
        h.attrs['mldata'] = config.VERSION_MLDATA

        h.close()