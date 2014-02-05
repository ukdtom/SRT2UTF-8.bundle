# Copyright (c) 2011-2012 Vit Suchomel and Jan Pomikalek
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

"""Character encoding detection library."""

import os
import sys
import struct

ENCODE_REPLACEMENT_CHARACTER = '\x00'
MODEL_VERSION = '1.3'

def list_models():
    "Returns a list of inbuilt models."
    models = []
    models_dir = os.path.join(
        os.path.dirname(sys.modules['chared'].__file__), 'models')
    for filename in os.listdir(models_dir):
        if filename.endswith('.edm'):
            models.append(filename.rsplit('.', 1)[0])
    return sorted(models)

def get_model_path(model_id):
    """
    Returns the full path to the model with given id or None if no model with
    the ID exists.
    """
    models_dir = os.path.join(
        os.path.dirname(sys.modules['chared'].__file__), 'models')
    filepath = os.path.join(models_dir, model_id + '.edm')
    if os.path.isfile(filepath):
        return filepath
    else:
        return None

def scalar_product(vec1, vec2):
    "Returns a scalar product of the two vectors."
    result = 0
    for key in vec1.keys():
        if vec2.has_key(key):
            result += vec1[key] * vec2[key]
    return result

def replace_by_zero(error):
    """
    Replaces unknown bytes while encoding/decoding.
    The function has to be registered using codecs.register_error.
    """
    if isinstance(error, UnicodeEncodeError):
        return (unicode(ENCODE_REPLACEMENT_CHARACTER), error.end)
    elif isinstance(error, UnicodeDecodeError):
        return (u'\ufffd', error.end)
    raise error


class EncodingDetector(object):
    VECTOR_TUPLE_LENGTH = 3

    def __init__(self, version=MODEL_VERSION, vectors={}, enc_order=()):
        self._version = version
        self._vectors = vectors
        self._encodings_order = enc_order

    def get_version(self):
        return self._version

    def save(self, path):
        """
        Saves the model to the specified path.
        File format:
        general row: <verison><TAB><tuple length><TAB><encodings count>
        for each encoding:
            info row: <name><TAB><order><TAB><vector length>
            vector row: <key><packed value>...
        """
        with open(path, 'wb') as fp:
            #basic attributes
            fp.write('%s\t%d\t%d\n' % 
                (self._version, self.VECTOR_TUPLE_LENGTH, len(self._vectors)))
            #vectors
            for enc, vector in self._vectors.iteritems():
                #encoding name, encoding order
                vect_len = len(vector)
                enc_order = self.get_encoding_order(enc)
                fp.write('%s\t%d\t%d\n' % (enc, enc_order, vect_len))
                #vector keys & values
                for k, v in vector.iteritems():
                    fp.write('%s%s' % (k, struct.pack('=I', v)))
                fp.write('\n')

    @classmethod
    def load(cls, path):
        """
        Loads the model from the specified path.
        Returns a new instance of EncodingDetector.
        """
        version = ''
        vectors = {}
        enc_order = {}


        with open(path, 'rb') as fp:
            #basic attributes
            version, vect_tuple_length, enc_count = fp.readline().split('\t')
            if MODEL_VERSION != version:
                sys.stderr.write('WARNING: Potentially incompatible model versions!\n')
                sys.stderr.write('\t%s: %s\n\tthis module: %s\n' % (path, version, MODEL_VERSION))
            vect_tuple_length = int(vect_tuple_length)
            #vectors
            for i in range(int(enc_count)):
                #encoding name, encoding order
                enc, order, vect_len = fp.readline().split('\t')
                enc_order[int(order)] = enc
                #vector keys & values
                vectors[enc] = {}
                for j in range(int(vect_len)):
                    key = fp.read(vect_tuple_length)
                    vectors[enc][key] = struct.unpack('=I', fp.read(4))[0]
                fp.read(1)
        return EncodingDetector(version, vectors, enc_order.values())

    def vectorize(self, string):
        """
        Transforms the input strings into a frequency vector of n-grams of 
        contained characters.
        Omits vector keys containing the encoding replacement character.
        """
        str_len = len(string)
        if self.VECTOR_TUPLE_LENGTH > str_len:
            return {}
        vector = {}
        for i in range(str_len - self.VECTOR_TUPLE_LENGTH + 1):
            key = string[i:i + self.VECTOR_TUPLE_LENGTH]
            if ENCODE_REPLACEMENT_CHARACTER not in key:
                vector[key] = vector.get(key, 0) + 1
        return vector

    def train(self, string, encoding):
        "Trains the detector. The input must be a string and its encoding."
        self._vectors[encoding] = self.vectorize(string)

    def set_encodings_order(self, encodings):
        """
        Defines the order (importance / frequency of use) of the encodings
        the classifier has been trained on. The input must be a list or a
        tuple of encodings. The first is the most important and the last is
        the least important.
        """
        if not isinstance(encodings, (tuple, list)):
            raise TypeError
        self._encodings_order = tuple(encodings)

    def get_encoding_order(self, encoding):
        """
        Returns the order of the encoding or sys.maxint if no order is
        defined for it.
        """
        if encoding in self._encodings_order:
            return self._encodings_order.index(encoding)
        return sys.maxint

    def classify(self, string):
        """
        Returns the predicted character encoding(s) for the input string as
        a list. The list may contain more than one element if there are
        multiple equally likely candidates. In this case, the candidates are
        returned in the order of importance (see set_encodings_order). Empty
        list may be returned if there are no valid candidates. 
        """
        input_vector = self.vectorize(string)
        classification = []
        for clas, vector in self._vectors.iteritems():
            score = scalar_product(input_vector, vector)
            clas_info = {'clas': clas, 'score': score,
                'order': self.get_encoding_order(clas)}
            classification.append(clas_info)

        if not classification:
            return []

        #order result classes 
        # 1.) by vector similarity score (higher score is better)
        # 2.) by the encoding order (lower index is better)
        classification.sort(lambda x, y:
            cmp(y['score'], x['score']) or cmp(x['order'], y['order']))

        #return a list of the top classes
        # the top classes have the same score and order as the first one
        first = classification[0]
        result = []
        for clas in classification:
            if first['score'] == clas['score']:
                result.append(clas['clas'])
        return result

    def reduce_vectors(self):
        """
        Remove the common parts of all vectors. Should be called after all
        training data has been loaded. Provided the training has been performed
        on the same data for all encodings, reducing vectors increases both
        efficiency and accuracy of the classification.
        """
        #get frequencies of (key, value) pairs
        key_value_count = {}
        for vect in self._vectors.values():
            for key, value in vect.iteritems():
                key_value_count[(key, value)] = key_value_count.get(
                    (key, value), 0) + 1
        #remove common parts of vectors (the (key, value) pairs with the
        #frequency equal to the number of vectors)
        encodings_count = len(self._vectors)
        for (key, value), count in key_value_count.iteritems():
            if count >= encodings_count:
                for vect in self._vectors.values():
                    if vect.has_key(key):
                        del vect[key]
