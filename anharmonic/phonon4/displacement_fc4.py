import numpy as np
from phonopy.harmonic.displacement import get_least_displacements, \
    get_displacement, directions_axis, is_minus_displacement
from anharmonic.phonon3.displacement_fc3 import get_reduced_site_symmetry, get_least_orbits, get_next_displacements, get_bond_symmetry
from anharmonic.file_IO import write_supercells_with_three_displacements

def get_fourth_order_displacements(cell,
                                   symmetry,
                                   is_plusminus='auto',
                                   is_diagonal=False):
    # Atoms 1, 2, and 3 are defined as follows:
    #
    # Atom 1: The first displaced atom. Fourth order force constant
    #         between Atoms 1, 2, 3, and 4 is calculated.
    # Atom 2: The second displaced atom. Third order force constant
    #         between Atoms 2, 3, and 4 is calculated.
    # Atom 3: The third displaced atom. Second order force constant
    #         between Atoms 3 and 4 is calculated.
    # Atom 4: Force is mesuared on this atom.

    # Least displacements for third order force constants
    #
    # Data structure
    # [{'number': atom1,
    #   'displacement': [0.00000, 0.007071, 0.007071],
    #   'second_atoms': [ {'number': atom2,
    #                      'displacement': [0.007071, 0.000000, 0.007071],
    #                      'third_atoms': [ {'number': atom3,
    #                                        'displacements':
    #                                       [[-0.007071, 0.000000, -0.007071],
    #                                        ,...]}, {...}, ... ]},

    # Least displacements of first atoms (Atom 1) are searched by
    # using respective site symmetries of the original crystal.
    disps_first = get_least_displacements(symmetry,
                                          is_plusminus=is_plusminus,
                                          is_diagonal=False)

    symprec = symmetry.get_symmetry_tolerance()

    dds = []
    for disp in disps_first:
        atom1 = disp[0]
        disp1 = disp[1:4]
        site_sym = symmetry.get_site_symmetry(atom1)

        dds_atom1 = {'number': atom1,
                     'direction': disp1,
                     'second_atoms': []}
        reduced_site_sym = get_reduced_site_symmetry(site_sym, disp1, symprec)
        second_atoms = get_least_orbits(atom1,
                                        cell,
                                        reduced_site_sym,
                                        symprec)
        
        for atom2 in second_atoms:
            reduced_bond_sym = get_bond_symmetry(
                reduced_site_sym,
                cell.get_scaled_positions(),
                atom1,
                atom2,
                symprec)

            for disp2 in _get_displacements_second(reduced_bond_sym,
                                                   symprec,
                                                   is_diagonal):
                dds_atom2 = _get_second_displacements(atom2,
                                                      disp2,
                                                      cell,
                                                      reduced_bond_sym,
                                                      symprec,
                                                      is_diagonal)
                dds_atom1['second_atoms'].append(dds_atom2)
        dds.append(dds_atom1)

    write_supercells_with_three_displacements(cell, dds)


    return dds

def _get_displacements_second(reduced_bond_sym,
                              symprec,
                              is_diagonal):
    if is_diagonal:
        disps_second = get_displacement(reduced_bond_sym)
    else:
        disps_second = get_displacement(reduced_bond_sym, directions_axis)

    disps_second_with_minus = []
    for disp2 in disps_second:
        disps_second_with_minus.append(disp2)
        if is_minus_displacement(disp2, reduced_bond_sym):
            disps_second_with_minus.append(-disp2)

    return disps_second_with_minus

def _get_second_displacements(atom2,
                              disp2,
                              cell,
                              reduced_bond_sym,
                              symprec,
                              is_diagonal):
    positions = cell.get_scaled_positions()
    dds_atom2 = {'number': atom2,
                 'direction': disp2,
                 'third_atoms': []}
    reduced_bond_sym2 = get_reduced_site_symmetry(reduced_bond_sym,
                                                  disp2,
                                                  symprec)
    third_atoms = get_least_orbits(atom2,
                                   cell,
                                   reduced_bond_sym2,
                                   symprec)

    for atom3 in third_atoms:
        reduced_plane_sym = get_bond_symmetry(
            reduced_bond_sym2,
            cell.get_scaled_positions(),
            atom2,
            atom3,
            symprec)
        dds_atom3 = get_next_displacements(atom2,
                                           atom3,
                                           reduced_plane_sym,
                                           positions,
                                           symprec,
                                           is_diagonal)
        dds_atom2['third_atoms'].append(dds_atom3)

    return dds_atom2
