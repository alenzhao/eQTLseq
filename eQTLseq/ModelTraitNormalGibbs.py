"""Implements ModelTraitNormalGibbs."""

import numpy as _nmp
import numpy.random as _rnd

import eQTLseq.utils as _utils


class ModelTraitNormalGibbs(object):
    """A normal model of Bayesian variable selection through shrinkage for a single trait estimated using Gibbs."""

    def __init__(self, **args):
        """TODO."""
        n_markers, n_iters = args['n_markers'], args['n_iters']

        # initial conditions
        self.tau = _rnd.rand()
        self.zeta = _rnd.rand(n_markers)
        self.beta = _rnd.normal(0, 1, size=n_markers)

        self.idxs = _nmp.ones(n_markers, dtype='bool')

        self._trace = _nmp.empty(n_iters + 1)
        self._trace.fill(_nmp.nan)
        self._trace[0] = 0

        self.tau_sum, self.tau2_sum = 0, 0
        self.zeta_sum, self.zeta2_sum = _nmp.zeros(n_markers), _nmp.zeros(n_markers)
        self.beta_sum, self.beta2_sum = _nmp.zeros(n_markers), _nmp.zeros(n_markers)

    def update(self, itr, **args):
        """TODO."""
        Y, G, YTY, GTG, GTY = args['Y'], args['G'], args['YTY'], args['GTG'], args['GTY']
        n_burnin, beta_thr = args['n_burnin'], args['beta_thr']
        n_samples, _ = G.shape

        self.idxs = _nmp.abs(self.beta) > beta_thr

        G = G[:, self.idxs]
        GTY = GTY[self.idxs]
        GTG = GTG[:, self.idxs][self.idxs, :]

        zeta = self.zeta[self.idxs]

        # sample beta, tau and zeta
        beta, tau = _sample_beta_tau(YTY, GTG, GTY, zeta, n_samples)
        zeta = _sample_zeta(beta, tau)

        self._trace[itr] = _calculate_joint_log_likelihood(Y, G, beta, tau, zeta)

        self.beta[self.idxs] = beta
        self.zeta[self.idxs] = zeta
        self.tau = tau

        if(itr > n_burnin):
            self.tau_sum += self.tau
            self.zeta_sum += self.zeta
            self.beta_sum += self.beta

            self.tau2_sum += self.tau**2
            self.zeta2_sum += self.zeta**2
            self.beta2_sum += self.beta**2

    @property
    def trace(self):
        """TODO."""
        return self._trace

    def get_estimates(self, **args):
        """TODO."""
        n_iters, n_burnin = args['n_iters'], args['n_burnin']

        N = n_iters - n_burnin
        tau_mean, zeta_mean, beta_mean = self.tau_sum / N, self.zeta_sum / N, self.beta_sum / N
        tau_var, zeta_var, beta_var = self.tau2_sum / N - tau_mean**2, self.zeta2_sum / N - zeta_mean**2, \
            self.beta2_sum / N - beta_mean**2

        return {
            'tau': tau_mean, 'tau_var': tau_var,
            'zeta': zeta_mean, 'zeta_var': zeta_var,
            'beta': beta_mean, 'beta_var': beta_var
        }


def _sample_beta_tau(YTY, GTG, GTY, zeta, n_samples):
    n_markers = zeta.shape[0]

    # sample tau
    shape = 0.5 * (n_markers + n_samples)
    rate = 0.5 * YTY
    tau = _rnd.gamma(shape, 1 / rate)

    # sample beta
    A = tau * (GTG + _nmp.diag(zeta))
    b = tau * GTY
    beta = _utils.sample_multivariate_normal(b, A)

    ##
    return beta, tau


def _sample_zeta(beta, tau):
    # sample tau_beta
    shape = 0.5
    rate = 0.5 * beta**2 * tau
    zeta = _rnd.gamma(shape, 1 / rate)

    ##
    return zeta


def _calculate_joint_log_likelihood(Y, G, beta, tau, zeta):
    n_samples, n_markers = G.shape

    resid = Y - (G * beta).sum(1)
    A = (0.5 * n_samples + 0.5 * n_markers - 1) * _nmp.log(tau)
    B = 0.5 * tau * (resid**2).sum()
    C = 0.5 * tau * (beta**2 * zeta).sum()
    D = 0.5 * _nmp.log(zeta).sum()

    #
    return (A - B - C - D) / n_markers
