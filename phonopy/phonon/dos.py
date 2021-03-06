# Copyright (C) 2011 Atsushi Togo
# All rights reserved.
#
# This file is part of phonopy.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
#
# * Neither the name of the phonopy project nor the names of its
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import numpy as np
from phonopy.phonon.tetrahedron_mesh import TetrahedronMesh


def write_total_dos(frequency_points,
                    total_dos,
                    comment=None):
    fp = open('total_dos.dat', 'w')
    if comment is not None:
        fp.write("# %s\n" % comment)

    for freq, dos in zip(frequency_points, total_dos):
        fp.write("%20.10f%20.10f\n" % (freq, dos))

def write_partial_dos(frequency_points,
                      partial_dos,
                      comment=None):
    fp = open('partial_dos.dat', 'w')
    if comment is not None:
        fp.write("# %s\n" % comment)
        
    for freq, pdos in zip(frequency_points, partial_dos.T):
        fp.write("%20.10f" % freq)
        fp.write(("%20.10f" * len(pdos)) % tuple(pdos))
        fp.write("\n")


def plot_total_dos(frequency_points,
                   total_dos,
                   freq_Debye=None,
                   Debye_fit_coef=None):
    import matplotlib.pyplot as plt
    plt.plot(frequency_points, total_dos, 'r-')

    if freq_Debye is not None:
        freq_pitch = frequency_points[1] - frequency_points[0]
        num_points = int(freq_Debye / freq_pitch)
        freqs = np.linspace(0, freq_Debye, num_points + 1)
        plt.plot(np.append(freqs, freq_Debye),
                 np.append(Debye_fit_coef * freqs**2, 0), 'b-')
    plt.grid(True)
    plt.xlim(min(frequency_points), max(frequency_points))
    plt.xlabel('Frequency')
    plt.ylabel('Density of states')
    
    return plt

def plot_partial_dos(frequency_points,
                     partial_dos,
                     indices=None,
                     legend=None):
    import matplotlib.pyplot as plt
    plt.grid(True)
    plt.xlim(min(frequency_points), max(frequency_points))
    plt.xlabel('Frequency')
    plt.ylabel('Partial density of states')
    plots = []

    num_atom = len(partial_dos)

    if indices == None:
        indices = []
        for i in range(num_atom):
            indices.append([i])

    for set_for_sum in indices:
        pdos_sum = np.zeros(frequency_points.shape, dtype='double')
        for i in set_for_sum:
            if i > num_atom - 1 or i < 0:
                print "Your specified atom number is out of range."
                raise ValueError
            pdos_sum += partial_dos[i]
        plots.append(plt.plot(frequency_points, pdos_sum))

    if not legend==None:
        plt.legend(legend)

    return plt
    
class NormalDistribution:
    def __init__(self, sigma):
        self._sigma = sigma

    def calc(self, x):
        return 1.0 / np.sqrt(2 * np.pi) / self._sigma * \
            np.exp(-x**2 / 2.0 / self._sigma**2)

class CauchyDistribution:
    def __init__(self, gamma):
        self._gamma = gamma

    def calc(self, x):
        return self._gamma / np.pi / (x**2 + self._gamma**2)


class Dos:
    def __init__(self, mesh_object, sigma=None, tetrahedron_method=False):
        self._mesh_object = mesh_object
        self._frequencies = mesh_object.get_frequencies()
        self._weights = mesh_object.get_weights()
        if tetrahedron_method:
            self._tetrahedron_mesh = TetrahedronMesh(self._mesh_object)
        else:
            self._tetrahedron_mesh = None

        self._frequency_points = None
        self._sigma = sigma
        self.set_draw_area()
        self.set_smearing_function('Normal')

    def set_smearing_function(self, function_name):
        """
        function_name ==
        'Normal': smearing is done by normal distribution.
        'Cauchy': smearing is done by Cauchy distribution.
        """
        if function_name == 'Cauchy':
            self._smearing_function = CauchyDistribution(self._sigma)
        else:
            self._smearing_function = NormalDistribution(self._sigma)

    def set_sigma(self, sigma):
        self._sigma = sigma

    def set_draw_area(self,
                      freq_min=None,
                      freq_max=None,
                      freq_pitch=None):

        f_min = self._frequencies.min()
        f_max = self._frequencies.max()

        if self._tetrahedron_mesh is not None:
            self._sigma = 0
        if self._sigma is None:
            self._sigma = (f_max - f_min) / 100
            
        if freq_min is None:
            f_min -= self._sigma * 10
        else:
            f_min = freq_min
            
        if freq_max is None:
            f_max += self._sigma * 10
        else:
            f_max = freq_max

        if freq_pitch is None:
            f_delta = (f_max - f_min) / 200
        else:
            f_delta = freq_pitch
        self._frequency_points = np.arange(f_min, f_max + f_delta * 0.1, f_delta)

class TotalDos(Dos):
    def __init__(self, mesh_object, sigma=None, tetrahedron_method=False):
        Dos.__init__(self,
                     mesh_object,
                     sigma=sigma,
                     tetrahedron_method=tetrahedron_method)
        self._dos = None
        self._freq_Debye = None
        self._Debye_fit_coef = None

    def run(self):
        if self._tetrahedron_mesh is None:
            self._dos = np.array([self._get_density_of_states_at_freq(f)
                                  for f in self._frequency_points])
        else:
            thm = self._tetrahedron_mesh
            thm.run_at_frequencies(value='I',
                                   frequency_points=self._frequency_points)
            iw = thm.get_integration_weights()
            self._dos = np.sum(np.dot(iw, self._weights), axis=1)

    def get_dos(self):
        """
        Return freqs and total dos
        """
        return self._frequency_points, self._dos

    def get_Debye_frequency(self):
        return self._freq_Debye

    def set_Debye_frequency(self, num_atoms, freq_max_fit=None):
        try:
            from scipy.optimize import curve_fit
        except ImportError:
            print "You need to install python-scipy."
            exit(1)

        def Debye_dos(freq, a):
            return a * freq**2

        freq_min = self._frequency_points.min()
        freq_max = self._frequency_points.max()
        
        if freq_max_fit is None:
            N_fit = len(self._frequency_points) / 4 # Hard coded
        else:
            N_fit = int(freq_max_fit / (freq_max - freq_min) *
                        len(self._frequency_points))
        popt, pcov = curve_fit(Debye_dos,
                               self._frequency_points[0:N_fit],
                               self._dos[0:N_fit])
        a2 = popt[0]
        self._freq_Debye = (3 * 3 * num_atoms / a2)**(1.0 / 3)
        self._Debye_fit_coef = a2

    def plot_dos(self):
        return plot_total_dos(self._frequency_points,
                              self._dos,
                              freq_Debye=self._freq_Debye,
                              Debye_fit_coef=self._Debye_fit_coef)

    def write(self):
        if self._tetrahedron_mesh is None:
            comment = "Sigma = %f" % self._sigma
        else:
            comment = "Tetrahedron method"
            
        write_total_dos(self._frequency_points,
                        self._dos,
                        comment=comment)

    def _get_density_of_states_at_freq(self, f):
        return np.sum(np.dot(
            self._weights, self._smearing_function.calc(self._frequencies - f))
            ) /  np.sum(self._weights)


class PartialDos(Dos):
    def __init__(self,
                 mesh_object,
                 sigma=None,
                 tetrahedron_method=False,
                 direction=None):
        Dos.__init__(self,
                     mesh_object,
                     sigma=sigma,
                     tetrahedron_method=tetrahedron_method)
        self._eigenvectors = self._mesh_object.get_eigenvectors()

        num_atom = self._frequencies.shape[1] / 3
        i_x = np.arange(num_atom, dtype='int') * 3
        i_y = np.arange(num_atom, dtype='int') * 3 + 1
        i_z = np.arange(num_atom, dtype='int') * 3 + 2
        if direction is not None:
            self._direction = np.array(
                direction, dtype='double') / np.linalg.norm(direction)
            proj_eigvecs = self._eigenvectors[:, i_x, :] * self._direction[0]
            proj_eigvecs += self._eigenvectors[:, i_y, :] * self._direction[1]
            proj_eigvecs += self._eigenvectors[:, i_z, :] * self._direction[2]
            self._eigvecs2 = np.abs(proj_eigvecs) ** 2
        else:
            self._direction = None
            self._eigvecs2 = np.abs(self._eigenvectors[:, i_x, :]) ** 2
            self._eigvecs2 += np.abs(self._eigenvectors[:, i_y, :]) ** 2
            self._eigvecs2 += np.abs(self._eigenvectors[:, i_z, :]) ** 2
        self._partial_dos = None

    def run(self):
        if self._tetrahedron_mesh is None:
            self._run_smearing_method()
        else:
            self._run_tetrahedron_method()

    def _run_smearing_method(self):
        pdos = []
        weights = self._weights / float(np.sum(self._weights))
        for freq in self._frequency_points:
            amplitudes = self._smearing_function.calc(self._frequencies - freq)
            pdos.append(self._get_partial_dos_at_freq(amplitudes, weights))
        self._partial_dos = np.transpose(pdos)

    def _run_tetrahedron_method(self):
        num_freqs = len(self._frequency_points)
        num_atom = self._eigvecs2.shape[1]
        self._partial_dos = np.zeros((num_atom, num_freqs), dtype='double')
        thm = self._tetrahedron_mesh
        thm.run_at_frequencies(value='I',
                               frequency_points=self._frequency_points)
        iw = thm.get_integration_weights()
        for j in range(num_freqs):
            for i, w in enumerate(self._weights):
                for ib, frac in enumerate(self._eigvecs2[i].T):
                    self._partial_dos[:, j] += iw[j, ib, i] * frac * w
        
    def get_partial_dos(self):
        """
        frequency_points: Sampling frequencies
        partial_dos: [atom_index, frequency_points_index]
        """
        return self._frequency_points, self._partial_dos

    def plot_pdos(self, indices=None, legend=None):
        return plot_partial_dos(self._frequency_points,
                                self._partial_dos,
                                indices=indices,
                                legend=legend)
    
    def write(self):
        if self._tetrahedron_mesh is None:
            comment = "Sigma = %f" % self._sigma
        else:
            comment = "Tetrahedron method"
            
        write_partial_dos(self._frequency_points,
                          self._partial_dos,
                          comment=comment)

    def _get_partial_dos_at_freq(self, amplitudes, weights):
        num_band = self._frequencies.shape[1]
        pdos = [(np.dot(weights, self._eigvecs2[:, i, :] * amplitudes)).sum()
                for i in range(num_band / 3)]
        return pdos

