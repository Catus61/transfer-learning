import h5py

from tools import build_transfer_net
from tools.datasets.urban_tribes import load_data


class Session(object):
    """Training session.

    This is a helper class to bundle model and history together and make it
    easy to resume training and recording history.
    """
    def __init__(self, model, history=None):
        self.model = model
        self.history = history

    def dump(self, path):
        W, b = self.model.layers[-1].get_weights()
        with h5py.File(path, 'w') as f:
            f.create_dataset('W', data=W)
            f.create_dataset('b', data=b)
            group = f.create_group('history')
            for k, v in self.history.items():
                group.create_dataset(k, data=v)

    @classmethod
    def load(cls, model, path):
        with h5py.File(path, 'r') as f:
            W = f['W'][:]
            b = f['b'][:]
            history = {}
            for k, v in f['history'].items():
                history[k] = list(v)
        model.layers[-1].set_weights([W, b])
        return cls(model, history=history)

    def train(self, *args, **kwargs):
        new_history = self.model.fit(*args, **kwargs)
        self._record(new_history.history)

    def _record(self, new_history):
        if self.history is None:
            self.history = new_history
        else:
            for key in self.history.keys():
                self.history[key].extend(new_history[key])


def transfer_learn(layer_name, nb_sample, nb_epoch, output_file):
    """Transfer learning for image classification.

    Args:
        layer_name: Transfer layer name.
        nb_sample: Number of samples per categories.
        nb_epoch: Number of epochs to train.
        output_file: Name of the output file to pick history to.
    """
    # Build model
    model = build_transfer_net(output_dim=11,
                               transfer_layer_name=layer_name)

    # Prepare data
    (x_train, y_train), (x_val, y_val), (x_test, y_test) = \
        load_data(images_per_category=nb_sample)

    # Train
    model.compile(optimizer='adadelta', loss='categorical_crossentropy',
                  metrics=['accuracy'])
    session = Session(model)
    session.train(x_train, y_train, batch_size=nb_sample, nb_epoch=nb_epoch,
                  validation_data=(x_val, y_val))
    session.dump(output_file)
    return session
