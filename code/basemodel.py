import copy
import statistics
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import tensorflow as tf
import tensorflow_datasets as tfds
from nltk import sent_tokenize
from tensorflow.keras.layers import Layer
from tensorflow.keras import backend as K
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer
from factory_embeddings import FactoryEmbeddings
from abc import abstractmethod
# import tensorflow_docs as tfdocs  # To use in the future.
# import tensorflow_docs.modeling
# import tensorflow_docs.plots
from tensorflow.keras.callbacks import ReduceLROnPlateau, EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam, RMSprop
from sklearn.metrics import classification_report, accuracy_score, roc_auc_score, f1_score, precision_score, \
    recall_score
from preprocessing import Preprocessing
from sklearn.model_selection import train_test_split

SEED = 42


class BaseModel(Layer):

    def __init__(self, max_len, path_train, path_test, path_dev, epochs, learning_rate, optimizer,
                 load_embeddings, batch_size=32, embedding_size='300', emb_type='fasttext', l2_rate=1e-5,
                 vocabulary=None, vocab_size=None, max_sequence_len=None, rate=0.2, length_type='median',
                 dense_units=128, both_embeddings=False, filters=64, kernel_size=5, pool_size=2, buffer_size=3):
        super(BaseModel).__init__()
        self._vocabulary = vocabulary
        self.max_len = max_len
        self.path_train = path_train
        self.path_test = path_test
        self.path_dev = path_dev
        self.batch_size = batch_size
        self.embeddings_matrix = None
        self.embedding_size = embedding_size
        self.emb_type = emb_type
        self.max_sequence_len = max_sequence_len
        self._vocab_size = None
        self.train = None
        self.test = None
        self.dev = None
        self.MAX_NB_WORDS = vocab_size
        self.X_train = None
        self.X_test = None
        self.X_dev = None
        self.y_train = None
        self.y_test = None
        self.y_dev = None
        self._vocab_index = None
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.init_learning_rate = 0.0001
        self.length_type = length_type
        self.OPTIMIZERS = {
            'adam': Adam(learning_rate=self.learning_rate, beta_1=0.9, beta_2=0.98, epsilon=1e-9),
            'rmsprop': RMSprop(learning_rate == self.learning_rate)
        }
        self.optimizer = self.OPTIMIZERS[optimizer]
        self.load_embeddings = load_embeddings
        self.model = None
        self.pos = 5737
        self.neg = 45557
        self.total = 51294
        self.weight_for_0 = (1 / self.neg) * self.total / 2.0
        self.weight_for_1 = (1 / self.pos) * self.total / 2.0
        self.class_weights = {0: self.weight_for_0, 1: self.weight_for_1}
        print('Weight for class 0: {:.2f}'.format(self.weight_for_0))
        print('Weight for class 1: {:.2f}'.format(self.weight_for_1))
        self.rate = rate
        self.l2_rate = l2_rate
        self.dense_units = dense_units
        self.METRICS = [
            # tf.keras.metrics.TruePositives(name='tp'),
            # tf.keras.metrics.FalsePositives(name='fp'),
            # tf.keras.metrics.TrueNegatives(name='tn'),
            # tf.keras.metrics.FalseNegatives(name='fn'),
            tf.keras.metrics.BinaryAccuracy(name='accuracy'),
            # tf.keras.metrics.Precision(name='precision'),
            # tf.keras.metrics.Recall(name='recall'),
            # self.precision_m,
            # self.recall_m,
            # self.f1_m,
            # BaseModel.precision,
            # BaseModel.recall,
            # tf.keras.metrics.AUC(name='auc')
        ]
        self.initial_bias = abs(np.log([self.pos / self.neg]))
        self.initial_bias = self.pos / self.total
        self.history = None
        self.word_index = None
        self.both_embeddings = both_embeddings
        if self.both_embeddings:
            self.nb_words_glove = None
            self.nb_words_ft = None
            self.embeddings_matrix_glove = None
            self.embeddings_matrix_ft = None
        else:
            self.nb_words = None
            self.embeddings_matrix = None
        self.checkpoint_filepath = './checkpoints/checkpoint_attention.cpk'
        self.model_save = ModelCheckpoint(filepath=self.checkpoint_filepath, save_weights_only=True, mode='auto',
                                          monitor='loss', save_best_only=True)
        self.reduce_lr = ReduceLROnPlateau(monitor='loss', patience=5, factor=0.5, verbose=1, mode='auto',
                                           min_lr=(5e-5))
        self.early_stop = EarlyStopping(
            monitor='val_loss', patience=5, verbose=1, mode='min',
            baseline=None, restore_best_weights=True
        )
        self.callbacks = [self.model_save, self.reduce_lr]  # , self.early_stop]
        # In case of a CNN Layer
        self.filters = filters
        self.kernel_size = kernel_size
        self.pool_size = pool_size
        self.buffer_size = buffer_size
        self.print_configuration()

    def recall_m(self, y_true, y_pred):
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
        recall = true_positives / (possible_positives + K.epsilon())
        return recall

    def precision_m(self, y_true, y_pred):
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
        precision = true_positives / (predicted_positives + K.epsilon())
        return precision

    def f1_m(self, y_true, y_pred):
        precision = self.precision_m(y_true, y_pred)
        recall = self.recall_m(y_true, y_pred)
        return 2 * ((precision * recall) / (precision + recall + K.epsilon()))

    @property
    def vocab_size(self):
        return self._vocab_size

    @property
    def vocabulary(self):
        return self._vocabulary

    @property
    def vocab_index(self):
        return self._vocab_index

    @property
    def testpred(self):
        return self.y_test

    @property
    def devpred(self):
        return self.y_dev

    @property
    def mean_length(self):
        return 583

    @property
    def mode_length(self):
        return 282

    @property
    def median_length(self):
        return 461

    @property
    def max_length(self):
        return 600

    def print_configuration(self):
        print('MODEL CONFIGURATION')
        print('Max Sequence Length: ' + str(self.max_sequence_len))
        print('Epochs for training: ' + str(self.epochs))
        print('Bath Size: ' + str(self.batch_size))
        print('Embeddings Selected: ' + self.emb_type)
        print('Dense Units: ' + str(self.dense_units))
        print('Learning Rate: ' + str(self.learning_rate))
        print('Dropout Rate: ' + str(self.rate))
        print('L2 Regularization Rate: ' + str(self.l2_rate))

    def load_data(self):
        """Load the 3 DataFrames, train-test-dev. The data here will be preprocessed, previously tokenized,
        stopwords deleted and stem.
        """
        # Load train-test-dev data
        self.train = pd.read_csv(self.path_train, sep='\t')
        self.train.loc[self.train['label'] == -1, 'label'] = 0
        self.test = pd.read_csv(self.path_test, sep='\t')
        self.test.loc[self.test['label'] == -1, 'label'] = 0
        if self.path_dev is not None:
            self.dev = pd.read_csv(self.path_dev, sep='\t')
            self.dev.loc[self.dev['label'] == -1, 'label'] = 0
        # Change the label column to categorical.
        self.y_train = tf.keras.utils.to_categorical(self.train['label'], num_classes=2)
        # self.y_train = self.train['label'].astype('category')
        self.y_test = tf.keras.utils.to_categorical(self.test['label'], num_classes=2)
        # self.y_test = self.test['label'].astype('category')
        if self.path_dev is not None:
            self.y_dev = tf.keras.utils.to_categorical(self.dev['label'], num_classes=2)
            # self.y_dev = self.dev['label'].astype('category')

    def pad_sentences(self):
        """Function that pad all the sentences  to the max_len parameter from the class.
        First it tokenize the data with tensorflow tokenizer and then apply the pad_sequences function
        """
        tokenizer = Tokenizer(num_words=self.max_len, lower=True, char_level=False)
        if self.path_dev is not None:
            full_text = pd.concat([self.train.text, self.test.text, self.dev.text])
        else:
            full_text = pd.concat([self.train.text, self.test.text])
        tokenizer.fit_on_texts(full_text)
        word_seq_train = tokenizer.texts_to_sequences(self.train['text'])
        word_seq_test = tokenizer.texts_to_sequences(self.test['text'])
        if self.path_dev is not None:
            word_seq_dev = tokenizer.texts_to_sequences(self.dev['text'])

        self.word_index = tokenizer.word_index

        if self.length_type.lower() == 'fixed':
            print('Se usará {} como max_sequence_len.', self.max_sequence_len)
        elif self.length_type.lower() == 'mean':
            print('Se usará la media como max_sequence_len.')
            self.max_sequence_len = self.__mean_padding(word_seq_train)
        elif self.length_type.lower() == 'mode':
            print('Se usará la moda como max_sequence_len.')
            self.max_sequence_len = self.__mode_padding(word_seq_train)
        elif self.length_type.lower() == 'median':
            print('Se usará la mediana como max_sequence_len.')
            self.max_sequence_len = self.__median_padding(word_seq_train)
        else:
            print('The padding used will be the fixed one.')
        print('The max_sequence_len is: ', self.max_sequence_len)

        self.X_train = pad_sequences(word_seq_train, maxlen=self.max_sequence_len)
        self.X_test = pad_sequences(word_seq_test, maxlen=self.max_sequence_len)
        if self.path_dev is not None:
            self.X_dev = pad_sequences(word_seq_dev, maxlen=self.max_sequence_len)

        self.tokenizer=tokenizer

    def __mean_padding(self, text):
        lst = []
        for sequence in text:
            lst.append(len(sequence))
        return int(statistics.mean(lst))

    def __mode_padding(self, text):
        lst = []
        for sequence in text:
            lst.append(len(sequence))
        return int(statistics.mode(lst))

    def __median_padding(self, text):
        lst = []
        for sequence in text:
            lst.append(len(sequence))
        return int(statistics.median(lst))

    def __sentence_median_padding(self, text):
        """Function that calculate the median of sentences in the text to pad the mean_model to that maximum
        sentences per sequence.
        Args:
            - text: List or pandas series with all the sequence to get the median
        Returns:
            - The padding to apply
        """
        lst = []
        for sequence in text:
            lst.append(len(sent_tokenize(sequence)))
        return int(statistics.median(lst))

    def load_vocabulary(self):
        """Function that extract the vocabulary from the train DataFrame. This functions will be used with it's needed
        to use random embeddings.
        """
        # TODO: Calculate vocabulary from data
        pass

    def create_embeddings_matrix(self):
        """Function that create the embedding matrix
        """
        if self.both_embeddings is False:
            self.nb_words, self.embeddings_matrix = self.create_1_embedding_matrix(self.emb_type)
        else:
            self.nb_words_glove, self.embeddings_matrix_glove = self.create_1_embedding_matrix('glove')
            self.nb_words_ft, self.embeddings_matrix_ft = self.create_1_embedding_matrix('fasttext')

    def create_1_embedding_matrix(self, type=None):
        """Function that create the embedding matrix
        """
        self.emb = FactoryEmbeddings()
        self.emb.load_embeddings(type)
        embeddings = self.emb.embeddings.embeddings_full
        words_not_found = []
        # Se calcula el número máximo de palabras de nuestro vocabulario
        print('Word index: ' + str(len(self.word_index)))
        nb_words = max(self.max_len, len(self.word_index))
        # Se crea la matriz de embeddings
        embeddings_matrix = np.zeros((nb_words, self.embedding_size))
        # self.nb_words = min(self.max_len, len(self.word_index))
        # self.embeddings_matrix = np.zeros((self.nb_words, self.embedding_size))

        for word, i in self.word_index.items():
            # if i >= nb_words:
            #     continue
            embedding_vector = embeddings.get(word)
            if embedding_vector is not None and len(embedding_vector) > 0:
                embeddings_matrix[i] = embedding_vector
            else:
                words_not_found.append(word)
        print('Total number of null words: %d' % np.sum(np.sum(embeddings_matrix, axis=1) == 0))
        return nb_words, embeddings_matrix

    def preprare_mean_document_embeddings(self):
        if self.emb is None:
            self.emb = FactoryEmbeddings()
            self.emb.load_embeddings(self.emb_type)
        self.max_sentences_in_sequence = self.train.text
        print('El número máximo de sentencias a usar es de: ', self.max_sentences_in_sequence)
        self.mean_embeddings = self.emb.embeddings.calc_embeddings(self.train.text, self.max_sequence_len,
                                                                   self.max_sentences_in_sequence)
        self.mean_embeddings_test = self.emb.embeddings.calc_embeddings(self.test.text, self.max_sequence_len,
                                                                        self.max_sentences_in_sequence)
        if self.path_dev is not None:
            self.mean_embeddings_dev = self.emb.embeddings.calc_embeddings(self.dev.text, self.max_sequence_len,
                                                                           self.max_sentences_in_sequence)

    def prepare_data(self):
        print('Loading data')
        self.load_data()
        print('Padding sentences')
        self.pad_sentences()
        print('Tras padding')
        print('Loading Vocabulary and Embeddings Matrix')
        self.create_embeddings_matrix()

    def prepare_data_v2(self):
        self.prepare_data()
        self.preprare_mean_document_embeddings()
        self.X_train = [self.X_train, self.mean_embeddings]
        self.X_test = [self.X_test, self.mean_embeddings_test]
        if self.path_dev is not None:
            self.X_dev = [self.X_dev, self.mean_embeddings_dev]

    def prepare_data_v3(self):
        self.prepare_data()
        self.train_data_aux = pd.read_csv('../data/train_aux_data.tsv', sep='\t')
        self.test_data_aux = pd.read_csv('../data/test_aux_data.tsv', sep='\t')
        self.dev_data_aux = pd.read_csv('../data/dev_aux_data.tsv', sep='\t')
        self.train_aux = self.train_data_aux['FactLabel']
        self.test_aux = self.test_data_aux['FactLabel']
        self.dev_aux = self.dev_data_aux['FactLabel']
        unique_labels = pd.unique(self.test_aux)
        # There are 4 more labels on train than in test-dev fact label, and as they are derivations from
        # 'Extreme Right, Propaganda, Conspiracy', we convert them to that value.
        for i in range(len(self.train_aux)):
            if self.train_aux[i] not in unique_labels:
                self.train_aux[i] = 'Extreme Right, Propaganda, Conspiracy'
        # Once we've converted it, we one hot them
        self.train_aux = pd.get_dummies(self.train_aux)
        self.test_aux = pd.get_dummies(self.test_aux)
        self.dev_aux = pd.get_dummies(self.dev_aux)
        if self.train_aux.shape[1] != self.test_aux.shape[1]:
            print(self.train_aux.shape)
            print(self.test_aux.shape)
            raise ValueError("Shapes are differents!")
        self.X_train = [self.X_train, self.train_aux]
        self.X_test = [self.X_test, self.test_aux]
        if self.path_dev is not None:
            self.X_dev = [self.X_dev, self.dev_aux]

    def prepare_data_as_tensors(self):
        self.prepare_data()
        print('Loading data as tensors')
        # Load data as tensors
        self.train_dataset = tf.data.Dataset.from_tensor_slices((self.X_train, self.y_train))
        self.train_dataset = self.train_dataset.shuffle(len(self.X_train)).batch(self.batch_size)

        if self.path_dev is not None:
            self.val_dataset = tf.data.Dataset.from_tensor_slices((self.X_dev, self.y_dev))
            self.val_dataset = self.val_dataset.shuffle(len(self.X_dev)).batch(self.batch_size)

    def prepare_data_as_tensors_v2(self):
        self.prepare_data()
        self.preprare_mean_document_embeddings()
        print('Loading data as tensors')
        # Load data as tensors
        self.train_dataset = tf.data.Dataset.from_tensor_slices(
            ({'seq_input': self.X_train, 'mean_emb': self.mean_embeddings}, self.y_train))
        self.train_dataset = self.train_dataset.shuffle(len(self.X_train)).batch(self.batch_size)
        print(self.train_dataset)
        if self.path_dev is not None:
            self.val_dataset = tf.data.Dataset.from_tensor_slices(
                ({'seq_input': self.X_dev, 'mean_emb': self.mean_embeddings_dev}, self.y_dev))
            self.val_dataset = self.val_dataset.shuffle(len(self.X_dev)).batch(self.batch_size)

        """
        # TODO: Prepare val_dataset as tensor using train_dataset
        else:
            train_size = int(0.9 * len(self.X_train))
            val_size = int(0.1 * len(self.X_train))
            self.full_dataset = tf.data.Dataset.from_tensor_slices((self.X_train, self.y_train))
            self.train_dataset = self.full_dataset.shuffle(len(self.X_train)).batch(self.batch_size)
            self.train_dataset = self.full_dataset.take(train_size)
            self.val_dataset = self.full_dataset.skip(train_size)
            self.val_dataset = self.val_dataset.skip(val_size)
            self.val_dataset = self.val_dataset.take(val_size)
        """

    def fit(self, with_validation=False):
        """Fit the model using the keras fit function.
        Arguments:
            - with_validation (bool): If True test data is applied as validation set
        """
        tf.random.set_seed(SEED)
        if not with_validation:
            self.history = self.model.fit(self.X_train, self.y_train, batch_size=self.batch_size, epochs=self.epochs,
                                          verbose=1,
                                          callbacks=self.callbacks, shuffle=True, class_weight=self.class_weights)
        elif self.path_dev is not None:
            self.history = self.model.fit(self.X_train, self.y_train, batch_size=self.batch_size, epochs=self.epochs,
                                          verbose=1,
                                          callbacks=self.callbacks, shuffle=True,
                                          validation_data=(self.X_dev, self.y_dev),
                                          class_weight=self.class_weights)
        else:
            self.history = self.model.fit(self.X_train, self.y_train, batch_size=self.batch_size, epochs=self.epochs,
                                          verbose=1, callbacks=self.callbacks, shuffle=True, validation_split=0.1,
                                          class_weight=self.class_weights)
        print('Salgo de fit')

    def fit_as_tensors(self, with_validation=False):
        """Fit the model using the keras fit function. The data must be loaded using the prepare_data_as_tensors
        function.
        Arguments:
            - with_validation (bool): If True test data is applied as validation set
        """
        tf.random.set_seed(SEED)
        if not with_validation:
            self.history = self.model.fit(self.train_dataset, epochs=self.epochs, verbose=1, callbacks=self.callbacks,
                                          class_weight=self.class_weights)
        # elif self.path_dev is not None:
        #     self.history = self.model.fit(self.train_dataset, epochs=self.epochs, verbose=1, callbacks=self.callbacks,
        #                                   class_weight=self.class_weights, validation_data=self.val_dataset)
        else:
            X_train_data, X_val_data, y_train_label, y_val_label = train_test_split(self.X_train, self.y_train,
                                                                                    test_size=0.1, random_state=42)
            self.train_dataset = tf.data.Dataset.from_tensor_slices((X_train_data, y_train_label))
            self.train_dataset = self.train_dataset.shuffle(len(X_train_data)).batch(self.batch_size)
            self.val_dataset = tf.data.Dataset.from_tensor_slices((X_val_data, y_val_label))
            self.val_dataset = self.val_dataset.shuffle(len(X_val_data)).batch(self.batch_size)
            self.history = self.model.fit(self.train_dataset, epochs=self.epochs, verbose=1, callbacks=self.callbacks,
                                          class_weight=self.class_weights, validation_data=self.val_dataset)

    @abstractmethod
    def call(self):
        pass

    def predict(self):
        """Make the prediction for the test/dev data. It uses the data from the own class.
        """
        # Actually it works as a test function to prove that the code is working.
        print('TEST SET')
        preds = self.model.predict(self.X_test, batch_size=self.batch_size, verbose=0)
        real_preds = []
        for p in preds:
            if p[0] > p[1]:
                real_preds.append(0)
            else:
                real_preds.append(1)
        print(real_preds[:10])
        y_true = []
        for p in self.y_test:
            if p[0] > p[1]:
                y_true.append(0)
            else:
                y_true.append(1)

        print(classification_report(y_true, real_preds))
        print('Roc auc score: ', roc_auc_score(y_true, real_preds))
        print('Accuracy: ', accuracy_score(y_true, real_preds))
        print('Precision-Propaganda: ', precision_score(y_true, real_preds))
        print('Recall-Propaganda: ', recall_score(y_true, real_preds))
        print('F1-Propaganda: ', f1_score(y_true, real_preds))
        print('Macro F1-Propaganda: ', f1_score(y_true, real_preds, average='macro'))

    def predict_dev(self):
        """Make the prediction for the test/dev data. It uses the data from the own class.
                """
        # Actually it works as a test function to prove that the code is working.
        print('DEV SET')
        preds = self.model.predict(self.X_dev, batch_size=self.batch_size, verbose=0)
        real_preds = []
        for p in preds:
            if p[0] > p[1]:
                real_preds.append(0)
            else:
                real_preds.append(1)
        print(real_preds[:10])
        y_true = []
        for p in self.y_dev:
            if p[0] > p[1]:
                y_true.append(0)
            else:
                y_true.append(1)

        print(classification_report(y_true, real_preds))
        print('Roc auc score: ', roc_auc_score(y_true, real_preds))
        print('Accuracy: ', accuracy_score(y_true, real_preds))
        print('Precision-Propaganda: ', precision_score(y_true, real_preds))
        print('Recall-Propaganda: ', recall_score(y_true, real_preds))
        print('F1-Propaganda: ', f1_score(y_true, real_preds))
        print('Macro F1-Propaganda: ', f1_score(y_true, real_preds, average='macro'))

    def predict_test_dev(self):
        self.predict()
        self.predict_dev()