'''
Input using DeepSpeech.
'''

import numpy
import os
import pyaudio

from   deepspeech         import Model
from   dexter.input       import Token
from   dexter.input.audio import AudioInput
from   dexter.core.log    import LOG

# ------------------------------------------------------------------------------

# In order to use this module you'll need to ensure that you have enough memory
# since its requirements are relatively huge. On a Raspberry Pi this means
# increasing your swap size to about 1G.
#
# So far I haven't been able to make the Pi work with the language model owing
# to memory constraints; even with 4G of swap.
#
# It's still _very_ slow on a Pi; well over a minute for a few seconds of audio.

# ------------------------------------------------------------------------------

# Typical installation location for deepspeech data
_MODEL_DIR = "/usr/local/share/deepspeech/models"

# Beam width used in the CTC decoder when building candidate transcriptions
_BEAM_WIDTH = 500

# These constants are tied to the shape of the graph used (changing them changes
# the geometry of the first layer), so make sure you use the same constants that
# were used during training

# Number of MFCC features to use
_NUM_FEATURES = 26

# Size of the context window used for producing timesteps in the input vector
_NUM_CONTEXT = 9

# The alpha hyperparameter of the CTC decoder. Language Model weight
_LM_WEIGHT = 1.75

# The beta hyperparameter of the CTC decoder. Word insertion weight (penalty)
_WORD_COUNT_WEIGHT = 1.00

# Valid word insertion weight. This is used to lessen the word insertion penalty
# when the inserted word is part of the vocabulary
_VALID_WORD_COUNT_WEIGHT = 1.00

# ------------------------------------------------------------------------------

class DeepSpeechInput(AudioInput):
    '''
    Input from DeepSpeech using the US English language model.
    '''
    def __init__(self,
                 notifier,
                 use_lm=False,
                 wav_dir=None):
        '''
        @see AudioInput.__init__()

        @type  use_lm: bool
        @param use_lm:
            Whether to use the DeepSpeech language model for better predictions.
        '''
        super(DeepSpeechInput, self).__init__(
            notifier,
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            wav_dir=wav_dir
        )

        # The files which we'll need from the model directory
        alphabet = os.path.join(_MODEL_DIR, 'alphabet.txt')
        model    = os.path.join(_MODEL_DIR, 'output_graph.pb')
        lm       = os.path.join(_MODEL_DIR, 'lm.binary')
        trie     = os.path.join(_MODEL_DIR, 'trie')

        # If these don't exist then DeepSpeech will segfault when inferring!
        if not os.path.exists(alphabet):
            raise IOError("Not found: %s" % alphabet)
        if not os.path.exists(model):
            raise IOError("Not found: %s" % model)

        # Load in the model.
        LOG.info("Loading %s" % model)
        self._model = Model(model,
                            _NUM_FEATURES,
                            _NUM_CONTEXT,
                            alphabet,
                            _BEAM_WIDTH)

        # If we're using a language model then pull that in too. This requires a
        # decent chunk of memory.
        if use_lm:
            if not os.path.exists(lm):
                raise IOError("Not found: %s" % lm)
            if not os.path.exists(trie):
                raise IOError("Not found: %s" % trie)

            LOG.info("Loading %s" % lm)
            self._model.enableDecoderWithLM(alphabet,
                                            lm,
                                            trie,
                                            _LM_WEIGHT,
                                            _VALID_WORD_COUNT_WEIGHT)


    def _decode_raw(self, data):
        '''
        @see AudioInput._decode_raw()
        '''
        audio = numpy.frombuffer(data, numpy.int16)
        words = self._model.stt(audio, self._rate)
        LOG.info("Got: %s" % (words,))
        tokens = [Token(word.strip(), 1.0, True)
                  for word in words.split(' ')
                  if len(word.strip()) > 0]
        return tokens
