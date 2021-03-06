import numpy as np
import math
import scipy.optimize as sciopt
import pymc
from matplotlib import pyplot as plt
from scipy import stats, interpolate
from astroML.stats.random import linear
from astroML.plotting.mcmc import convert_to_stdev
from astroML.density_estimation import GaussianMixture1D


def max_entropy_dice_priors(nsides = 6, mu=3.5):
    """Estimates the Baysian priors for the faces of an N-sided die, using only the mean value mu and the principle of maximum entropy."""
    #First, compute lambda1:
    lambda1 = sciopt.newton(compute_lambda1,1.,args=(nsides,mu))
    #Then, use that to get lambda0:
    lambda0 = sciopt.newton(compute_lambda0,1.,args=(lambda1,nsides,mu))

    #Finally, compute the probabilities on each face:
    ivals = np.linspace(1.,nsides,nsides)
    pivals = np.exp(-1.-lambda0)*np.exp(-ivals*lambda1)/float(nsides)
    print lambda0,lambda1
    print pivals

def compute_lambda1(lambda1,nsides,mu):
    ivals = np.linspace(1.,nsides,nsides)
    expvals = np.exp(-ivals*lambda1)
    return mu - np.sum(ivals*expvals)/np.sum(expvals)
def compute_lambda0(lambda0,lambda1,nsides,mu):
    ivals = np.linspace(1.,nsides,nsides)
    expvals = np.exp(-ivals*lambda1)
    return 1 - np.sum(expvals)*np.exp(-1-lambda0)/float(nsides)

def logL_gaussian(xi, yi, a, b):
    """gaussian log-likelihood (Eq. 5.87)"""
    xi = xi.ravel()
    yi = yi.ravel()
    a = a.reshape(a.shape + (1,))
    b = b.reshape(b.shape + (1,))
    yyi = a * xi + b
    return -0.5 * np.sum(np.log(yyi) + (yi - yyi) ** 2 / yyi, -1)


def logL_poisson(xi, yi, a, b):
    """poisson log-likelihood (Eq. 5.88)"""
    xi = xi.ravel()
    yi = yi.ravel()
    a = a.reshape(a.shape + (1,))#This is slightly faster than a[:,None], also guarantees new index will be added to the end of the array. Both are neat though!
    b = b.reshape(b.shape + (1,))
    yyi = a * xi + b

    return np.sum(yi * np.log(yyi) - yyi, -1)

def compute_5_15():
    # Original Author: Jake VanderPlas
    # Modified by Andrew Schechtman-Rook
    # License: BSD
    #   This code is based on code used to make a figure in the textbook
    #   "Statistics, Data Mining, and Machine Learning in Astronomy" (2013)
    #   For more information, see http://astroML.github.com
    #   To report a bug or issue, use the following forum:
    #    https://groups.google.com/forum/#!forum/astroml-general
    #------------------------------------------------------------
    # Draw points from distribution
    np.random.seed(0)

    N = 1000

    a_true = 0.01
    xmin = 0.0
    xmax = 10.0
    b_true = 1. / (xmax - xmin) - 0.5 * a_true * (xmax + xmin)

    lin_dist = linear(xmin, xmax, a_true)
    data = lin_dist.rvs(N)

    #------------------------------------------------------------
    # Compute and plot the results
    fig = plt.figure(figsize=(9, 9))
    fig.subplots_adjust(left=0.1, right=0.95, wspace=0.3,
                        bottom=0.1, top=0.95, hspace=0.2)

    a = np.linspace(0.00001, 0.04, 71)
    b = np.linspace(0.00001, 0.15, 71)

    for num, nbins in enumerate([5, 100]):
        # divide points into bins
        yi, bins = np.histogram(data, bins=np.linspace(xmin, xmax, nbins + 1))
        xi = 0.5 * (bins[:-1] + bins[1:])

        # compute likelihoods for Poisson and Gaussian models
        factor = N * (xmax - xmin) * 1. / nbins
        #LP = logL_poisson(xi, yi, factor * a, factor * b[:, None])
        #LG = logL_gaussian(xi, yi, factor * a, factor * b[:, None])#Below is faster, marginally, probably also better practice
        LP = logL_poisson(xi, yi, factor * a, factor * b.reshape(b.shape + (1,)))
        LG = logL_gaussian(xi, yi, factor * a, factor * b.reshape(b.shape + (1,)))

        LP -= np.max(LP)
        LG -= np.max(LG)

        # find maximum likelihood point
        i, j = np.where(LP == np.max(LP))
        aP, bP = a[j[0]], b[i[0]]

        i, j = np.where(LG == np.max(LG))
        aG, bG = a[j[0]], b[i[0]]

        # plot scatter and lines
        ax = fig.add_subplot(2, 2, 1 + 2 * num)
        plt.scatter(xi, yi, s=9, c='gray', lw=0)

        x = np.linspace(xmin - 1, xmax + 1, 1000)
        for (ai, bi, s) in [(a_true, b_true, '-k'),
                            (aP, bP, '--k'),
                            (aG, bG, '-.k')]:
            px = ai * x + bi
            px[x < xmin] = 0
            px[x > xmax] = 0
            ax.plot(x, factor * px, s)

        ax.set_xlim(xmin - 1, xmax + 1)
        ax.set_xlabel('$x$')
        ax.set_ylabel('$y_i$')

        ax.text(0.04, 0.96,
                r'$\rm %i\ points$' % N + '\n' + r'$\rm %i\ bins$' % nbins,
                ha='left', va='top', transform=ax.transAxes)

        # plot likelihood contours
        ax = fig.add_subplot(2, 2, 2 + 2 * num)

        ax.contour(a, b, convert_to_stdev(LP),
                   levels=(0.683, 0.955, 0.997),
                   colors='k', linewidths=2)

        ax.contour(a, b, convert_to_stdev(LG),
                   levels=(0.683, 0.955, 0.997),
                   colors='gray', linewidths=1, linestyle='dashed')

        # trick the legend command
        ax.plot([0], [0], '-k', lw=2, label='Poisson Likelihood')
        ax.plot([0], [0], '-', c='gray', lw=1, label='Gaussian Likelihood')
        ax.legend(loc=1)

        # plot horizontal and vertical lines
        #  in newer matplotlib versions, use ax.vlines() and ax.hlines()
        ax.plot([a_true, a_true], [0, 0.2], ':k', lw=1)
        ax.plot([0, 0.06], [b_true, b_true], ':k', lw=1)

        ax.set_xlabel(r'$a^\ast$')
        ax.set_ylabel(r'$b^\ast$')

        ax.set_xlim(0, 0.04)
        ax.set_ylim(0.001, 0.15)

        ax.xaxis.set_major_locator(plt.MultipleLocator(0.02))

    fig.savefig('chap_5_5-15.png',dpi=300)

def likelihood_5_17(xi,mu1,g1,sig1,sig2):
    mu1_2d,g1_2d = np.meshgrid(mu1,g1)
    gauss_pdf_sig1 = np.exp(-(xi-mu1_2d.reshape(mu1_2d.shape+(1,)))**2/(2.*sig1))/(sig1*np.sqrt(2.*math.pi))
    gauss_pdf_sig2 = np.exp(-(xi-mu1_2d.reshape(mu1_2d.shape+(1,)))**2/(2.*sig2))/(sig2*np.sqrt(2.*math.pi))
    product = np.prod(gauss_pdf_sig1[:,:,1:]+gauss_pdf_sig2[:,:,1:],axis=-1)
    coefficient = gauss_pdf_sig1[:,:,0]*g1_2d+(1.-g1_2d)*gauss_pdf_sig2[:,:,0]
    return coefficient*product,g1_2d
def compute_5_17():
    #Based on code from AstroML and used in Statistics, Data Mining, and Machine Learning in Astronomy

    #Set the number of points and their standard deviations for both distributions:
    N1 = 48
    N2 = 2
    mu = 0
    sig1 = 1
    sig2 = 5
    sig_reject = 10.*sig1
    reject_conf = 0.683 #Confidence level to reject outlier:

    sigs = np.zeros(N1+N2)
    sigs[:N1] = sig1
    sigs[N1:] = sig2

    xi = np.random.normal(mu,sigs)

    #Construct a mu1,g1 parameter space:
    mu1 = np.linspace(-5,5,100)
    g1 = np.linspace(0,1,50)

    l1,g1_2d = likelihood_5_17(xi[::-1],mu1,g1,sig1,sig_reject)
    l1 /= np.max(l1)

    ax = plt.figure().add_subplot(111)
    ax.imshow(l1,origin='lower',aspect='auto',cmap=plt.cm.binary,extent=[mu1[0],mu1[-1],g1[0],g1[-1]])
    ax.contour(mu1,g1,convert_to_stdev(np.log(l1)),levels=(0.683,0.955,0.997),colors='red')
    ax.figure.savefig('chap_5_5-17.png',dpi=300)

    #Check which points should be rejected:
    for i in range(len(xi)):
        newxi = np.roll(xi,-i)
        li,g1_2d = likelihood_5_17(newxi,mu1,g1,sig1,sig_reject)
        li /= np.max(li)
        stdevs = convert_to_stdev(np.log(li))
        g1_in_rejection = np.where(stdevs < reject_conf,g1_2d,np.ones(g1_2d.shape))
        print i,g1_in_rejection.min()

def mcmc_example():
    #The MCMC example from SDMML, modified a bit:
    sigma_true = 1.2
    mu_true = 0.0
    numpoints = 100

    #Generate random gaussian data:
    np.random.seed(2)
    xi = np.random.normal(loc=mu_true,scale=sigma_true,size=numpoints)

    #Define the priors:
    mu_p = pymc.Uniform('mu',-5,5)#Uniform prior on mu
    sigma_p = sigma_true#fixed (known) sigma
    tau_p = 1./sigma_p**2
    M = pymc.Normal('M',mu_p,tau_p,observed=True,value=xi)
    model = {'M':M,'mu':mu_p}

    #Run the model:
    S = pymc.MCMC(model)
    S.sample(20000,burn=10000)
    mu_sample = S.trace('mu')[:]

    #Print results:
    print "Bayesian (MCMC): {0:.3f} +/- {1:.3f}".format(np.mean(mu_sample),np.std(mu_sample))
    print "Frequentist: {0:.3f} +/- {1:.3f}".format(np.mean(xi),np.std(xi,ddof=1)/np.sqrt(numpoints))


if __name__ == "__main__":
    #max_entropy_dice_priors(nsides=6,mu=3.5)
    #max_entropy_dice_priors(nsides=6,mu=5.9)

    #compute_5_17()
    #mcmc_example()
