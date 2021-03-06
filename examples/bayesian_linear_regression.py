#!/usr/bin/env python
"""
Bayesian linear regression using mean-field variational inference.

Probability model:
    Bayesian linear model
    Prior: Normal
    Likelihood: Normal
Variational model
    Likelihood: Mean-field Gaussian
"""
import edward as ed
import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np

from edward.stats import norm

class LinearModel:
    """
    Bayesian linear regression for outputs y on inputs x.

    p((x,y), z) = Normal(y | x*z, lik_variance) *
                  Normal(z | 0, prior_variance),

    where z are weights, and with known lik_variance and
    prior_variance.

    Parameters
    ----------
    weight_dim : list
        Dimension of weights, which is dimension of input x dimension
        of output.
    lik_variance : float, optional
        Variance of the normal likelihood; aka noise parameter,
        homoscedastic variance, scale parameter.
    prior_variance : float, optional
        Variance of the normal prior on weights; aka L2
        regularization parameter, ridge penalty, scale parameter.
    """
    def __init__(self, weight_dim, lik_variance=0.01, prior_variance=0.01):
        self.weight_dim = weight_dim
        self.lik_variance = lik_variance
        self.prior_variance = prior_variance
        self.num_vars = (self.weight_dim[0]+1)*self.weight_dim[1]

    def mapping(self, x, z):
        """Linear transformation W*x + b"""
        m, n = self.weight_dim[0], self.weight_dim[1]
        W = tf.reshape(z[:m*n], [m, n])
        b = tf.reshape(z[m*n:], [1, n])
        # broadcasting to do (W*x) + b (e.g. 40x10 + 1x10)
        h = tf.matmul(x, W) + b
        h = tf.squeeze(h) # n_data x 1 to n_data
        return h

    def log_prob(self, xs, zs):
        """
        Calculates the unnormalized log joint density.

        Parameters
        ----------
        xs : tf.tensor
            n_data x (D + 1), where first column is outputs and other
            columns are inputs (features)
        zs : tf.tensor or np.ndarray
            n_minibatch x num_vars, where n_minibatch is the number of
            weight samples and num_vars is the number of weights

        Returns
        -------
        tf.tensor
            vector of length n_minibatch, where the i^th element is
            the log joint density of xs and zs[i, :]
        """
        y = xs[:, 0]
        x = xs[:, 1:]
        log_prior = -self.prior_variance * tf.reduce_sum(zs*zs, 1)
        mus = tf.pack([self.mapping(x, z) for z in tf.unpack(zs)])
        # broadcasting to do mus - y (n_minibatch x n_data - n_data)
        log_lik = -tf.reduce_sum(tf.pow(mus - y, 2), 1) / self.lik_variance
        return log_lik + log_prior

def build_toy_dataset(n_data=40, noise_std=0.1):
    ed.set_seed(0)
    D = 1
    x  = np.concatenate([np.linspace(0, 2, num=n_data/2),
                         np.linspace(6, 8, num=n_data/2)])
    y = 0.075*x + norm.rvs(0, noise_std, size=n_data)
    x = (x - 4.0) / 4.0
    x = x.reshape((n_data, D))
    y = y.reshape((n_data, 1))
    data = np.concatenate((y, x), axis=1) # n_data x (D+1)
    data = tf.constant(data, dtype=tf.float32)
    return ed.Data(data)

ed.set_seed(42)
model = LinearModel(weight_dim=[1,1])
variational = ed.MFGaussian(model.num_vars)
data = build_toy_dataset()

# Set up figure
fig = plt.figure(figsize=(8,8), facecolor='white')
ax = fig.add_subplot(111, frameon=False)
plt.ion()
plt.show(block=False)

def print_progress(self, t, losses, sess):
    if t % self.n_print == 0:
        print("iter %d loss %.2f " % (t, np.mean(losses)))

        # Sample functions from variational model
        mean, std = sess.run([self.variational.m, self.variational.s])
        rs = np.random.RandomState(0)
        zs = rs.randn(10, self.variational.num_vars) * std + mean
        zs = tf.constant(zs, dtype=tf.float32)
        inputs = np.linspace(-8, 8, num=400, dtype=np.float32)
        x = tf.expand_dims(tf.constant(inputs), 1)
        mus = tf.pack([self.model.mapping(x, z) for z in tf.unpack(zs)])
        outputs = sess.run(mus)

        # Get data
        y, x = sess.run([self.data.data[:, 0], self.data.data[:, 1]])

        # Plot data and functions
        plt.cla()
        ax.plot(x, y, 'bx')
        ax.plot(inputs, outputs.T)
        ax.set_ylim([-2, 3])
        plt.draw()

ed.MFVI.print_progress = print_progress
inference = ed.MFVI(model, variational, data)
inference.run(n_iter=5000, n_print=5)
