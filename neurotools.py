from pickle import load
import os
from numpy import array, diff, floor, zeros, log, mean, std, shape, \
    random, cumsum, histogram, where, arange, divide, exp, insert, \
    count_nonzero, bitwise_and, append
import random as rnd
from brian import units
from brian.units import second, volt, msecond
from brian import NeuronGroup, PoissonGroup, PulsePacket, SpikeGeneratorGroup
from warnings import warn


class SynchronousInputGroup:
    '''
    Synchronous input generator.
    This class is a generator that generates spike trains where:
    - N*sync spike trains are synchronous,
    - N*(1-sync) spike trains are independent Poisson realisations,
    - the spikes in the n*s synchronous spike trains are shifted by
    Gaussian jitter with standard deviation = `sigma`.

    Constructor Parameters
    ----------
    N : int
        Number of spike trains

    rate : brian Hz (frequency)
        Spike rate for each spike train (units: freq)

    sync : float
        Proportion of synchronous spike trains [0,1]

    jitter : brian second (time)
        Standard deviation of Gaussian random variable which is used to shift
        each spike in a synchronous spike train (units: time)

    dt : brian second (time)
        Simulation time step (default 0.1 ms)
    '''

    def __init__(self, N, rate, synchrony, jitter, dt=0.0001*second):
        self.N = N
        self.rate = rate
        self.sync = synchrony
        self.jitter = jitter
        self._dt = dt
        self._gen = self.configure_generators(self.N, self.rate, self.sync,\
                self.jitter, self._dt)

    def __call__(self):
        return self._gen

    def configure_generators(self, n, rate, sync, jitter, dt=0.0001*second):
        '''
        Synchronous input generator. This function is called by the parent
        class constructor. See the parent class' doc string for details.

        Parameters
        ----------
        n : int
            Number of spike trains

        rate : brian Hz (frequency)
            Spike rate for each spike train (units: freq)

        sync : float
            Proportion of synchronous spike trains [0,1]

        jitter : brian second (time)
            Standard deviation of Gaussian random variable which is used to
            shift each spike in a synchronous spike train (units: time)

        dt : brian second (time)
            Simulation time step (default 0.1 ms)

        Returns
        -------
        A list of generators with the specific temporal characeteristics
        (see parent constructor for details)

        '''
        if not(0 <= sync <= 1):
            warn("Synchrony should be between 0 and 1. Setting to 0")
            sync = 0

        spiketrains = []
        n_ident = int(floor(n*sync))   # number of identical spike trains
        st_ident = self.sync_inp_gen(n_ident, rate, jitter, dt)
        for i in range(n_ident):
            spiketrains.append(st_ident)

        for i in range(n_ident,n):
            spiketrains.append(self.sync_inp_gen(1, rate, 0*second, dt))

        return spiketrains

    def sync_inp_gen(self, n, rate, jitter, dt=0.0001*second):
        '''
        The synchronous input generator.
        This generator returns the same value (plus a random variate) n times
        before returning a new spike time. This can be used to generate
        n spike trains with the same base spike times, but with jitter applied
        to each spike.
        The n spike trains generated are equivalent to having a series of
        Gaussian pulse packets centred on each base time (t) with
        spread = jitter.

        Parameters
        ----------
        n : int
            Number of synchronous inputs. This defines the number of times
            the same base time (t) will used by the generator.

        rate : brian hertz (frequency)
            The average spike rate

        jitter : brian second (time)
            The jitter applied to each t

        dt : biran second (time)
            Simulation time step (default 0.1 ms)
        '''

        t = 0*second
        prev_t = t
        iter = n
        while(True):
            if iter == n:
                interval = random.exponential(1./rate)*second
                if interval < dt: # prevents spike stacking
                    interval = dt
                prev_t = t
                t += interval
                iter = 1
            else:
                iter += 1
            if (jitter > 0*second):
                jitt_variate = random.normal(0, jitter)*second
                if (t + jitt_variate) < (prev_t + dt):
                    # limits stacking warnings but has similar effect
                    jitt_variate = prev_t + dt - t
            else:
                jitt_variate = 0*second
            yield t + jitt_variate


def calibrate_frequencies(nrngrp, input_configs, f_out):



def loadsim(simname):
    '''
    Takes a simulation name and loads the data associated with the simulation.
    Searches current directory for:
        "simname.mem" (membrane potential data)
        "simname.out" (output spike trains)
        "simname.stm" (input spike trains)

    If any of the above is not found, the function returns an empty list
    for the respective variable.

    NOTE: Best to use brian.tools.datamanager.DataManager object where possible.

    Parameters
    ----------
    simname : string
        The name of the file containing the simulation data
        (excluding extensions)

    Returns
    -------
    mem, spiketrain, stm : numpy arrays
        Simulation data

    '''

    memname = simname+".mem"
    if (os.path.exists(memname)):
        mem = load(open(memname,"rb"))
    else:
        mem = array([])

    outname = simname+".out"
    if (os.path.exists(outname)):
        spiketrain = load(open(outname,"rb"))
    else:
        spiketrain = array([])

    stmname = simname+".stm"
    if (os.path.exists(stmname)):
        stm = load(open(stmname,"rb"))
    else:
        stm = array([])

    if ((not mem.size) and (not spiketrain.size) and (not stm.size)):
        warn("No simulation data exists with name `%s` \n" % simname)

    return mem, spiketrain, stm


def slope_distribution(v, w, rem_zero=True):
    '''
    Calculates the distribution of membrane potential slope values.

    Parameters
    ----------
    v : numpy array
        Membrane potential values as taken from brian.StateMonitor
    w : float or brian voltage
        Precision of distribution. Slope values are grouped based on the size
        of w and considered equal.
    rem_zero : bool, optional
        If True, the function ignores slope values equal to zero,
        which are caused by refractoriness and are of little interest.

    Returns
    -------
    dist : array
        The values of the distribution. See numpy.histogram for more
        information on the shape of the return array.

    See Also
    --------
    histogram
    '''

    dv = diff(v)
    if (rem_zero):
        dv = dv[dv != 0]

    nbins = (max(dv)-min(dv))/w
    nbins = int(nbins)
    dist = histogram(dv,nbins)
    return dist


def positive_slope_distribution(v, w):
    '''
    Calculates the distribution of positive membrane potential slope values.

    Parameters
    ----------
    v : numpy array
        Membrane potential values as taken from brian.StateMonitor
    w : float or brian voltage
        Precision of distribution. Slope values are grouped based on the size
        of w and considered equal (histogram bin size).

    Return
    -------
    dist : array
        The values of the distribution. See numpy.histogram for more
        information on the shape of the return array.

    See Also
    --------
    numpy.histogram
    '''

    dv = diff(v)
    dv = dv[dv > 0]
    nbins = (max(dv)-min(dv))/w
    nbins = int(nbins)
    dist = histogram(dv,nbins)
    return dist


def npss(v, spiketrain, v_th, w, dt=0.0001*second):
    '''
    Calculates the normalised pre-spike membrane potential slope.

    Parameters
    ----------
    v : numpy array
        Membrane potential values as taken from brian.StateMonitor
    spiketrain : numpy array
        Spike train of the membrane potential data in 'v'
        as taken from brian.SpikeMonitor
    v_th : brian voltage
        Neuron spike threshold
    w : brian second (time)
        Pre-spike window used to calculate spike triggered average
        and subsequently slope values
    dt : brian second (time)
        The simulation time step

    Returns
    -------
    m_slope : float
        The mean npss of the simulation
    slopes : list of float
        The individual npss values for each spike

    '''

    warn('Using deprecated function npss()')
    if (spiketrain.size <= 1):
        return 0,[0]

    '''
    Using the STA might be a processing hog. We could just as easily
    use the plain m calculation (V(t) - V(t-w))/w as w do in the new
    firing slope.
    Perhaps I could/should discard this function, or at least mark it as
    deprecated.
    '''
    (m,s,wins) = sta(v, spiketrain, w, dt)
    wins[:,-1] = v_th
    # remove first window
    wins = wins[1:,:]

    w_d = w/dt-1
    th_d = v_th/volt

    slopes = mean(diff(wins,axis=1),1)

    firstspiketime_d = int(spiketrain[0]*second/dt)
    v_reset = v[firstspiketime_d+1]
    isis = diff(spiketrain)/dt

    # lower bound calculation
    low_bound = (th_d-v_reset)/isis

    # upper bound calculation
    high_bound = (th_d-v_reset)/w_d
    slopes_norm = (slopes-low_bound)/(high_bound-low_bound)
    slopes_norm[slopes_norm < 0] = 0

    overmax = (slopes_norm > 1).nonzero()

    mean_slope = mean(slopes_norm)
    return mean_slope, slopes_norm




def firing_slope(mem, spiketrain, dt=0.0001*second, w=0.0001*second):
    """
    Returns the mean value and a list containing each individual values of the
    slopes of the membrane potential at the time of firing of each spike.

    Parameters
    ----------
    mem : numpy array
        Membrane potential as taken from brian.StateMonitor
    spiketrain : numpy array
        Spike times corresponding to the membrane potential data in `v`
    w : brian second (time)
        Slope window
    dt : brian second (time)
        Simulation time step (default 0.1 ms)

    Returns
    -------
    slope_avg : float
        The mean slope of the membrane potential for all threshold crossings
    slopes : numpy array
        The individual values of the membrane potential slope at each
        threshold crossing

    NOTE: Although the return values are untiless they represent volt/second
    values.

    TODO:
    - Make separate function that accepts a spike monitor, or dictionary
    and returns a dictionary of slope values, for brian compatibility.
    """

    w = max(w, dt)
    if len(spiketrain) < 2:
        return 0, array([])
    intervals = diff(spiketrain)
    intervals = insert(intervals, 0, spiketrain[0])
    windows = array([min(w, i*second-dt) for i in intervals])
    st_dt = spiketrain/dt
    st_dt = st_dt.astype(int)
    w_dt = (windows/dt).astype(int)
    slopes = (mem[st_dt]-mem[st_dt-w_dt])*volt/windows
    return mean(slopes), slopes


def norm_firing_slope(mem, spiketrain, th, tau,
                      dt=0.0001*second, w=0.0001*second):
    """
    This function will replace npss for calculating the normalised slope.
    It doesn't use the STA to calculate slopes, which should be faster.

    Parameters
    ----------
    mem : numpy array
        Membrane potential as taken from brian.StateMonitor
    spiketrain : numpy array
        Spike times corresponding to the membrane potential data in `v`
    th : brian volt (potential)
        Neuron's firing threshold
    tau : brian second (time)
        Neuron's membrane leak time constant
    dt : brian second (time)
        Simulation time step (default 0.1 ms)
    w : brian second (time)
        Slope window

    Returns
    -------
    slope_avg : float
        The mean slope of the membrane potential for all threshold crossings
    slopes : numpy array
        The individual values of the membrane potential slope at each
        threshold crossing

    NOTE: Although the return values are untiless they represent volt/second
    values.
    """

    if w < dt:
        w = dt
    if len(spiketrain) < 2:
        return 0, array([])
    spiketrain = spiketrain[spiketrain > w]  # discard spikes that occurred too early
    mslope, slopes = firing_slope(mem, spiketrain, dt, w)
    first_spike = spiketrain[0]
    first_spike_index = int(first_spike/dt)
    reset = mem[first_spike_index+1]*volt
    slope_max = (th-reset)/w
    '''
    Minimum slope is ISI dependent and requires time constant to calculate
    '''
    ISIs = diff(spiketrain)
    min_input = (th - reset)/(1-exp(-ISIs/tau))
    lowstart = reset + min_input * (1-exp(-(ISIs-w)/tau))
    slope_min = (th - lowstart)/w
    slopes_normed = (slopes[1:] - slope_min)/(slope_max - slope_min)
    #if min(slopes_normed) < 0 or max(slopes_normed) > 1:
    #    import matplotlib as mpl
    #    mpl.pyplot.plot(mem)
    #    mpl.pyplot.title("normalised slopes [%f, %f]" % (min(slopes_normed),
    #        max(slopes_normed)))
    #    mpl.pyplot.show()
    return mean(slopes_normed), slopes_normed


def sta(v, spiketrain, w, dt=0.0001*second):
    '''
    Calculates the Spike Triggered Average (currently only membrane potential)
    of the supplied data. Single neuron data only.
    This is the average waveform of the membrane potential in a period `w`
    before firing. The standard deviation and the individual windows are also
    returned.

    Parameters
    ----------
    v : numpy array
        Membrane potential values as taken from brian.StateMonitor
    spiketrain : numpy array
        Spike train of the membrane potential data in `v` as taken
        from brian.SpikeMonitor
    w : brian second (time)
        The pre-spike time window
    dt : brian second (time)
        Simulation time step (default 0.1 ms)

    Returns
    -------
    sta_avg : numpy array
        The spike triggered average membrane potential

    sta_std : numpy array
        The standard deviation of the sta_avg

    sta_wins : numpy array
        Two dimensional array containing all the pre-spike membrane potential
        windows
    '''

    if (len(spiketrain) <= 1):
        sta_avg = array([])
        sta_std = array([])
        sta_wins = array([])
        return sta_avg, sta_std, sta_wins

    w_d = int(w/dt) # window length in dt
    sta_wins = zeros((len(spiketrain),w_d))
    for i, st in enumerate(spiketrain):
        t_d = int(st/dt)
        if (w_d < t_d):
            w_start = t_d-w_d # window start position index
            w_end = t_d # window end index
            sta_wins[i,:] = v[w_start:w_end]
        else:
            '''
            We have two options here:
            (a) drop the spike
            (b) pad with zeroes
            --
            (a) would make the size of the `wins` matrix inconsistent with
            the number of spikes and one would expect the rows to match
            (b) can skew the average and variance calculations
            --
            Currently going with (b): if the number of spikes is small enough
            that one would skew the stats, I won't be looking at the stats
            anyway.
            '''
            w_start = 0
            w_end = t_d
            curwin = append(zeros(w_d-t_d), v[:t_d])
            sta_wins[i,:] = curwin
    sta_avg = mean(sta_wins,0)
    sta_std = std(sta_wins,0)

    return sta_avg, sta_std, sta_wins


def sync_inp(n, rate, s, sigma, dura, dt=0.0001*second):
    '''
    Generates synchronous spike trains and returns spiketimes compatible
    with Brian's MultipleSpikeGeneratorGroup function.
    In other words, the array returned by this module should be passed as the
    argument to the MulitpleSpikeGeneratorGroup in order to define it as an
    input group.

    Parameters
    ----------
    n : int
        Number of spike trains

    rate : brian Hz (frequency)
        Spike rate for each spike train (units: freq)

    s : float
        Proportion of synchronous spike trains [0,1]

    sigma : brian second (time)
        Standard deviation of Gaussian random variable which is used to shift
        each spike in a synchronous spike train (units: time)

    dura : brian second (time)
        Duration of each spike train (units: time)

    dt : brian second (time)
        Simulation time step (units: time)

    Returns
    -------
    spiketimes : list of list
        Each item on the list is a spike train. Each spike train is
        a list of spike times.
    '''

    if not(0 <= s <= 1):
        warn("Synchrony should be between 0 and 1. Setting to 1.")
        s = 1

    n_ident = int(floor(n*s))   # number of identical spike trains
    spiketrains = []
    st_ident = poisson_spikes(dura,rate,dt)
    for i in range(n_ident):
        spiketrains.append(add_gauss_jitter(st_ident,sigma,dt))

    for i in range(n_ident,n):
        spiketrains.append(poisson_spikes(dura,rate,dt))

    return spiketrains


def poisson_spikes(dura, rate, dt=0.0001*second):
    '''
    Generates a single spike train with exponentially distributed inter-spike
    intervals, i.e., a realisation of a Poisson process.
    Returns a list of spike times.

    Parameters
    ----------
    dura : brian second (time)
        Duration of spike train

    rate : brian Hz (frequency)
        Spike rate

    dt : brian second (time)
        Simulation time step (units: time)

    Returns
    -------
    spiketrain : list
        A spike train as a list of spike times
    '''

    spiketrain = []
    #   generate first interval
    while len(spiketrain) == 0:
        newinterval = random.exponential(1./rate)*second
        if newinterval < dt:
            newinterval = dt
        if newinterval < dura:
            spiketrain = [newinterval]
    #   generate intervals until we hit the duration
    while spiketrain[-1] < dura:
        newinterval = random.exponential(1./rate)*second
        if newinterval < dt:
            newinterval = dt
        spiketrain.append(spiketrain[-1]+newinterval)
    #   remove last spike overflow from while condition
    spiketrain = spiketrain[:-1]
    return spiketrain


def add_gauss_jitter(spiketrain,jitter,dt=0.0001*second):
    '''
    Adds jitter to each spike in the supplied spike train and returns the
    resulting spike train.
    Jitter is applied by adding a sample from a Gaussian random variable to
    each spike time.

    Parameters
    ----------
    spiketrain : list
        A spike train characterised as a list of spike times

    jitter : brian second (time)
        Standard deviation of Gaussian random variable which is added to each
        spike in a synchronous spike train (units: time)

    dt : brian second (time)
        Simulation time step (units: time)

    Returns
    -------
    jspiketrain : list
        A spike train characterised by a list of spike times
    '''

    if (jitter == 0*second):
        return spiketrain

    jspiketrain = spiketrain + random.normal(0, jitter, len(spiketrain))

    #   sort the spike train to account for ordering changes
    jspiketrain.sort()
    #   can cause intervals to become shorter than dt
    intervals = diff(jspiketrain)
    while min(intervals) < dt/second:
        index = where(intervals == min(intervals))[0][0]
        intervals[index]+=dt/second
    jspiketrain = cumsum(intervals)
    jspiketrain = [st*second for st in jspiketrain]
    return jspiketrain


def times_to_bin(spikes, dt=0.001*second, duration=None):
    '''
    Converts a spike train into a binary strings. Each bit is a bin of
    fixed width (dt).
    This function is useful for aligning a binary representation of a spike
    train to recordings of the respective membrane potential and for processing
    spike trains in binary format.

    Parameters
    ----------
    spiketimes : numpy array
        A spiketrain array from a brian SpikeMonitor

    dt : brian second (time)
        The width of each bin (default 1 ms)

    duration: brian second (time)
        The duration of the spike train. If `None`, the length of the spike
        train is determined by the last spike time. If a time is specified, the
        final spike train is either truncated (if duration < last_spike) or
        the spike train is padded with zeros.

    Returns
    -------
    bintimes : numpy array
        Array of 0s and 1s, respectively indicating the absence or presence
        of at least one spike in each bin. Information on potential multiple
        spikes in a bin is lost.
    '''

    if not len(spikes):
        # no spikes
        if duration is None:
            return spikes
        else:
            return zeros(duration/dt)
    st = divide(spikes,dt)
    st = st.astype('int')
    if duration is None:
        binlength = max(st)+1
    else:
        binlength = int(duration/dt)
    bintimes = zeros(binlength)
    if len(st) == 0:
        return bintimes
    if st[-1] > binlength:
        st = st[st < binlength]
    bintimes[st] = 1
    return bintimes


def times_to_bin_multi(spikes, dt=0.001*second, duration=None):
    spiketimes = []
    if isinstance(spikes, dict):
        spiketimes = array([st for st in spikes.itervalues()])
    elif isinstance(spikes, list) or isinstance(spikes, array):
        spiketimes = spikes
    else:
        raise TypeError('dictionary, list or array expected')
    if duration is None:
        # find the maximum value of all
        duration = max(recursiveflat(spiketimes))+float(dt)
    bintimes = array([times_to_bin(st, dt=dt, duration=duration)\
                                                    for st in spiketimes])
    return bintimes


def PSTH(spikes, bin=0.001*second, dt=0.001*second, duration=None):
    '''
    Similar to times_to_bin{_multi} though it doesn't discard multiple spikes
    in a single bin. Allows plotting of the PSTH. Returns the times of the bins
    and the number of spikes in each bin (much like a histogram).

    NB: Entire function can be replaced by a simple call to histogram with an
    appropriate bin size.
    '''
    if bin < dt:
        bin = dt
    spiketimes = []
    if isinstance(spikes, dict):
        spiketimes = array([st for st in spikes.itervalues()])
    elif isinstance(spikes, list) or isinstance(spikes, array):
        spiketimes = array(spikes)
    else:
        raise TypeError('dictionary, list or array expected')
    flatspikes = recursiveflat(spiketimes)
    if duration is None:
        duration = max(flatspikes)+float(dt)
    flatspikes = array(flatspikes)
    nbins = int(duration/bin)
    psth = zeros(nbins)
    for b in arange(0, nbins, 1):
        binspikes = bitwise_and(flatspikes >= b*bin,
                flatspikes < (b+1)*bin)
        psth[b] = count_nonzero(binspikes)
    return arange(0*second, duration*second, bin), psth


def CV(spiketrain):
    '''
    Calculates the coefficient of variation for a spike train or any supplied
    array of values

    Parameters
    ----------
    spiketrain : numpy array (or arraylike)
        A spike train characterised by an array of spike times

    Returns
    -------
    CV : float
        Coefficient of variation for the supplied values

    '''

    isi = diff(spiketrain)
    if len(isi) == 0:
        return 0.0

    avg_isi = mean(isi)
    std_isi = std(isi)
    return std_isi/avg_isi


def CV2(spiketrain):
    '''
    Calculates the localised coefficient of variation for a spike train or
    any supplied array of values

    Parameters
    ----------
    spiketrain : numpy array (or arraylike)
        A spike train characterised by an array of spike times

    Returns
    -------
    CV2 : float
        Localised coefficient of variation for the supplied values

    '''

    isi = diff(spiketrain)
    N = len(isi)
    if (N == 0):
        return 0

    mi_total = 0
    for i in range(N-1):
        mi_total = mi_total + abs(isi[i]-isi[i+1])/(isi[i]+isi[i+1])

    return mi_total*2/N


def IR(spiketrain):
    '''
    Calculates the IR measure for a spike train or any supplied array of values

    Parameters
    ----------
    spiketrain : numpy array (or arraylike)
        A spike train characterised by an array of spike times

    Returns
    -------
    IR : float
        IR measure for the supplied values

    '''



    isi = diff(spiketrain)
    N = len(isi)
    if (N == 0):
        return 0

    mi_total = 0
    for i in range(N-1):
        mi_total = mi_total + abs(log(isi[i]/isi[i+1]))

    return mi_total*1/(N*log(4))


def LV(spiketrain):
    '''
    Calculates the measure of local variation for a spike train or any
    supplied array of values

    Parameters
    ----------
    spiketrain : numpy array (or arraylike)
        A spike train characterised by an array of spike times

    Returns
    -------
    LV : float
        Measure of local variation for the supplied values

    '''


    isi = diff(spiketrain)
    N = len(isi)
    if (N == 0):
        return 0

    mi_total = 0
    for i in range(N-1):
        mi_total = mi_total + ((isi[i] - isi[i+1])/(isi[i] + isi[i+1]))**2

    return mi_total*3/N


def SI(spiketrain):
    '''
    Calculates the SI measure for a spike train or any supplied array of values

    Parameters
    ----------
    spiketrain : numpy array (or arraylike)
        A spike train characterised by an array of spike times

    Returns
    -------
    SI : float
        SI measure for the supplied values

    '''


    isi = diff(spiketrain)
    N = len(isi)
    if (N == 0):
        return 0

    mi_sum = 0
    for i in range(N-1):
        mi_sum = mi_sum + log(4*isi[i]*isi[i+1]/((isi[i]+isi[i+1])**2))

    return -1./(2*N*(1-log(2)))*mi_sum


def unitrange(start, stop, step):
    '''
    Returns a list in the same manner as the Python built-in range, but works
    with brian units.

    '''
    if not isinstance(start, units.Quantity):
        raise TypeError("unitrange: `start` argument is not a brian unit."
            "Use Python build-in range() or numpy.arange()")
    if not isinstance(stop, units.Quantity):
        raise TypeError("unitrange: `stop` argument is not a brian unit."
            "Use Python build-in range() or numpy.arange()")
    if not isinstance(step, units.Quantity):
        raise TypeError("unitrange: `step` argument is not a brian unit."
                        "Use Python build-in range() or numpy.arange()")
    if not start.has_same_dimensions(stop) \
            or not start.has_same_dimensions(step) \
            or not stop.has_same_dimensions(step):
        raise TypeError("Dimension mismatch in `unitrange`")

    x = start
    retlist = []
    while x < stop:
        retlist.append(x)
        x += step
    return retlist


def spike_period_hist(spiketimes, freq, duration, nbins=10, dt=0.0001*second):
    dt = float(dt)
    period = 1/freq  # in ms
    period = int(period/dt)  # in timesteps
    binwidth = period/nbins  # segment period into 10 bins
    bins = zeros(nbins)
    nper = int((duration/dt)/period)  # number of periods
    st_a = array(spiketimes)/dt
    for i in range(len(bins)):
        for p in range(nper):
            perstart = p*period
            inbin = st_a[(st_a >= perstart+i*binwidth) &
                    (st_a < perstart+(i+1)*binwidth-1)]
            bins[i] += len(inbin)
    left = arange(0, 1, 1./nbins)
    return left, bins


def recursiveflat(ndobject):
    """
    Recursive function that flattens a n-dimensional object such as an array
    or list. Must be accessible in the format ndobject[i].
    Returns a 1-d list.
    """
    if not len(ndobject):
        return ndobject
    elif shape(ndobject[0]) == ():
        return ndobject
    else:
        return recursiveflat([item for row in ndobject for item in row])



#def npss_ar(v, spiketrain, v_th, tau_m, w):
#    '''
#    BROKEN!!!
#    '''
#    warn("npss_ar: BROKEN! FIX ME!")
#    return 0, [0]
#    if (spiketrain.size <= 1):
#        return 0,[0]
#
#    (m,s,wins) = sta(v, spiketrain, w)
#    wins[:,-1] = v_th
#    # remove first window
#    wins = wins[1:,:]
#    slopes = mean(diff(wins,axis=1),1)
#    spiketime_d = int(spiketrain[0]*second/(0.0001*second))
#    v_reset = v[spiketime_d+1]*mV
#    #print("reset: ",v_reset
#    isis = diff(spiketrain)
#    isis = isis*second/(0.0001*second)
#    # lower bound calculation
#    low_bound = (v_th-v_reset)/isis
#    #print low_bound[2],"= (",v_th,"-",v_reset,")/",isis[2]
#    # upper bound calculation
#    t_decay = isis-w*second/(0.0001*second)
#    t_decay = array(t_decay,dtype=int)
#    t_decay_max = max(t_decay)
#    decay_max = v_reset*\
#            exp(-(array(range(t_decay_max))/(tau_m/(0.0001*second))))
#    high_start = decay_max[t_decay-1]
#    high_bound = (v_th/volt-high_start)/(w/(0.0001*second))
#    slopes_norm = (slopes-low_bound)/(high_bound-low_bound)
#    slopes_norm[slopes_norm < 0] = 0
#    overmax = (slopes_norm > 1).nonzero()
#    '''
#    if (size(overmax) > 0):
#        print "Normalised slope exceeds 1 in",size(overmax),"cases:"
#        print "H bound:",high_bound[overmax]
#        print "L bound:",low_bound[overmax]
#        print "Slopes :",slopes[overmax]
#        print "Norm sl:",slopes_norm[overmax]
#        print "ISIs   :",isis[overmax]
#    '''
#    mean_slope = mean(slopes_norm)
#    return mean_slope,slopes_norm
