"""Includes various functions for simulating genotypic and phenotypic data."""

import numpy as _nmp
import numpy.random as _rnd

import eQTLseq.utils as _utils


def simulate_genotypes(n_samples=1000, n_markers=100, MAF_range=(0.05, 0.5)):
    """Generate a matrix of genotypes, using a binomial model."""
    # compute MAFs for each genetic marker and compute genotypes
    MAF = _rnd.uniform(MAF_range[0], MAF_range[1], n_markers)
    G = _rnd.binomial(2, MAF, (n_samples, n_markers))   # assume ploidy=2

    # drop mono-morphic markers
    G = G[:, _nmp.std(G, 0) > 0]

    #
    return {'G': G, 'MAF': MAF}


def simulate_phenotypes(G, mu=None, phi=None, mdl='NBinomial', n_markers_causal=2, n_genes=100, n_genes_affected=10,
                        s2e=1, h2=0.5):
    """Simulate eQTLs or single traits."""
    args = locals()

    assert mdl in ('NBinomial', 'Normal', 'Poisson', 'Binomial')

    #
    fcn = {
        'Normal': _simulate_eQTLs_normal,
        'NBinomial': _simulate_eQTLs_nbinom,
        'Poisson': _simulate_eQTLs_poisson,
        'Binomial': _simulate_eQTLs_binom,
    }[mdl]

    #
    return fcn(**args)


def _simulate_eQTLs_normal(**args):
    """Simulate eQTLs with normally distributed gene expression data."""
    G = args['G']
    n_markers_causal = args['n_markers_causal']
    n_genes = args['n_genes']
    n_genes_affected = args['n_genes_affected']
    s2e = args['s2e']
    h2 = args['h2']

    n_samples, n_markers = G.shape
    assert n_markers >= n_markers_causal
    assert n_genes >= n_genes_affected

    # sample causal markers and affected genes
    idxs_markers_causal = _rnd.choice(n_markers, n_markers_causal, replace=False)
    idxs_genes_affected = _nmp.hstack([
        _rnd.choice(n_genes, (n_genes_affected, 1), replace=False) for _ in range(n_markers_causal)
    ])

    # compute causal coefficients
    s2g = h2 * s2e / (1 - h2)
    coefs = _nmp.zeros((n_genes, n_markers))
    coefs[idxs_genes_affected, idxs_markers_causal] = \
        _rnd.normal(0, _nmp.sqrt(s2g / n_markers_causal), (n_genes_affected, n_markers_causal))

    # compute phenotype
    G = (G - _nmp.mean(G, 0)) / _nmp.std(G, 0)
    Y = _rnd.normal(G.dot(coefs.T), _nmp.sqrt(s2e))

    #
    return {'Y': Y, 'coefs': coefs}


def _simulate_eQTLs_poisson(**args):
    """Simulate eQTLs with normally distributed gene expression data."""
    mu = args['mu']

    args['n_genes'] = mu.size if args['n_genes'] is None else args['n_genes']
    assert args['n_genes'] <= mu.size

    idxs = _rnd.choice(mu.size, args['n_genes'], replace=False)
    mu = mu[idxs]

    # compute phenotype
    res = _simulate_eQTLs_normal(**args)
    Z = _rnd.poisson(mu * _nmp.exp(res['Y']))

    #
    return {'Z': Z, 'mu': mu, 'coefs': res['coefs'], 'Y': res['Y']}


def _simulate_eQTLs_binom(**args):
    """Simulate eQTLs with normally distributed gene expression data."""
    mu = args['mu']

    args['n_genes'] = mu.size if args['n_genes'] is None else args['n_genes']
    assert args['n_genes'] <= mu.size

    idxs = _rnd.choice(mu.size, args['n_genes'], replace=False)
    mu = mu[idxs]

    # compute phenotype
    res = _simulate_eQTLs_normal(**args)
    pi = mu / (mu + _nmp.exp(-res['Y']))
    Z = _rnd.binomial(1e6, pi)

    #
    return {'Z': Z, 'mu': mu, 'coefs': res['coefs'], 'Y': res['Y']}


def _simulate_eQTLs_nbinom(**args):
    """Simulate eQTLs with normally distributed gene expression data."""
    mu = args['mu']
    phi = args['phi']
    G = args['G']

    args['n_genes'] = phi.size if args['n_genes'] is None else args['n_genes']
    assert args['n_genes'] <= phi.size

    idxs = _rnd.choice(phi.size, args['n_genes'], replace=False)
    mu, phi = mu[idxs], phi[idxs]

    # compute phenotype
    G = (G - _nmp.mean(G, 0)) / _nmp.std(G, 0)
    res = _simulate_eQTLs_normal(**args)
    # Z = _utils.sample_nbinom(mu * _nmp.exp(res['Y']), phi)
    Z = _utils.sample_nbinom(mu * _nmp.exp(G.dot(res['coefs'].T)), phi)

    #
    return {'Z': Z, 'mu': mu, 'phi': phi, 'coefs': res['coefs'], 'Y': res['Y']}