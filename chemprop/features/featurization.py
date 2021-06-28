from typing import List, Tuple, Union
from itertools import zip_longest
from rdkit import Chem
import torch
import numpy as np
from chemprop.rdkit import make_mol

# Atom feature sizes
MAX_ATOMIC_NUM = 100 ## limiting size of atoms available, will likely keep to just more organic compounds/smaller
## inTErESting!!
ATOM_FEATURES = {
    'atomic_num': list(range(MAX_ATOMIC_NUM)),
    'degree': [0, 1, 2, 3, 4, 5],
    'formal_charge': [-1, -2, 1, 2, 0],
    'chiral_tag': [0, 1, 2, 3],
    'num_Hs': [0, 1, 2, 3, 4],
    'hybridization': [
        Chem.rdchem.HybridizationType.SP,
        Chem.rdchem.HybridizationType.SP2,
        Chem.rdchem.HybridizationType.SP3,
        Chem.rdchem.HybridizationType.SP3D,
        Chem.rdchem.HybridizationType.SP3D2
    ],
}

# Distance feature sizes
PATH_DISTANCE_BINS = list(range(10))
THREE_D_DISTANCE_MAX = 20
THREE_D_DISTANCE_STEP = 1
THREE_D_DISTANCE_BINS = list(range(0, THREE_D_DISTANCE_MAX + 1, THREE_D_DISTANCE_STEP))

# len(choices) + 1 to include room for uncommon values; + 2 at end for IsAromatic and mass
ATOM_FDIM = sum(len(choices) + 1 for choices in ATOM_FEATURES.values()) + 2
EXTRA_ATOM_FDIM = 0
BOND_FDIM = 14
EXTRA_BOND_FDIM = 0
REACTION_MODE = None
EXPLICIT_H = False
REACTION = False

def get_atom_fdim(overwrite_default_atom: bool = False) -> int:
    """
    Gets the dimensionality of the atom feature vector.

    :param overwrite_default_atom: Whether to overwrite the default atom descriptors
    :return: the dimensionality of the atom feature vector.
    """
    return (not overwrite_default_atom) * ATOM_FDIM + EXTRA_ATOM_FDIM

def set_explicit_h(explicit_h: bool) -> None:
    """
    Sets whether RDKit molecules will be constructed with explicit Hs.

    :param explicit_h: boolean whether to keep explicit Hs from input.
    """
    global EXPLICIT_H
    EXPLICIT_H = explicit_h

def set_reaction(reaction: bool, mode: str) -> None:
    """
    Sets whether to use a reaction or molecule as input and adopts feature dimensions

    :param reaction: Boolean whether to except reactions as input
    :param mode: Reaction mode to construct atom and bond feature vectors
   
    """
    global REACTION
    REACTION = reaction
    if reaction:
        global REACTION_MODE
        global EXTRA_BOND_FDIM
        global EXTRA_ATOM_FDIM

        EXTRA_ATOM_FDIM = ATOM_FDIM - MAX_ATOMIC_NUM - 1
        EXTRA_BOND_FDIM = BOND_FDIM
        REACTION_MODE = mode


def is_explicit_h() -> bool:
    r"""Returns whether to use + retain explicit Hs"""
    return EXPLICIT_H

def is_reaction() -> bool:
    r"""Returns whether to use reactions as input"""
    return REACTION

def reaction_mode() -> str:
    r"""Returns the reaction mode"""
    return REACTION_MODE

def set_extra_atom_fdim(extra):
    """Change the dimensionality of the atom feature vector"""
    global EXTRA_ATOM_FDIM
    EXTRA_ATOM_FDIM = extra

def get_bond_fdim(atom_messages: bool = False,
                  overwrite_default_bond: bool = False,
                  overwrite_default_atom: bool = False) -> int:
    """
    Gets dimensionality of bond feature vector.

    :param atom_messages: whether atom messages are being used. If atom messages are used,
    then just contains bond features,otherwise it contains both atom + bond features
    :param overwrite_default_bond: whether to overwrite the default bond descriptors
    :param overwrite_default_atom: whether to overwrite the default atom descriptors
    :return: dimensionality of bond feature vector.
    """
def set_extra_bond_fdim(extra):
    """Change the dimensionality of the bond feature vector."""
    global EXTRA_BOND_FDIM
    EXTRA_BOND_FDIM = extra


def onek_encoding_unk(value: int, choices: List[int]) -> List[int]:
    """
    Creates a one-hot encoding with an extra category for uncommon values.

    :param value: The value for which the encoding should be one.
    :param choices: list of possible values
    :return: a one-hot encoding of the :code:`value` in a list of length :code:`len(choices) + 1`.
            If :code:`value` is not in :code:`choices`, then the final element in the encoding is 1.
    """
    encoding = [0] * (len(choices) + 1)
    index = choices.index(value) if value in choices else -1
    encoding[index] = 1

    return encoding

def atom_features(atom: Chem.rdchem.Atom, functional_groups: List[int] = None) -> List[Union[bool, int, float]]:
    """
    Builds a feature vector for an atom.

    :param atom: an RDKit atom.
    :param functional_groups: a k-hot vecotr indicating the functional groups the atom belongs to
    :return: a list containing the atom features.
    """
    if atom is None:
        features = [0] * ATOM_FDIM
    else:
        features = onek_encoding_unk(atom.GetAtomicNum() - 1, ATOM_FEATURES['atomic_num']) + \
            onek_encoding_unk(atom.GetTotalDegree(), ATOM_FEATURES['degree']) + \
            onek_encoding_unk(atom.GetFormalCharge(), ATOM_FEATURES['formal_charge']) + \
            onek_encoding_unk(int(atom.GetChiralTag()), ATOM_FEATURES['chiral_tag']) + \
            onek_encoding_unk(int(atom.GetTotalNumHs()), ATOM_FEATURES['num_hs']) + \
            onek_encoding_unk(int(atom.GetHybridization()), ATOM_FEATURES['hybridization']) + \
            [1 if atom.GetIsAromatic() else 0] + \
            [atom.GetMass() * 0.01] # scaled to about the same range as other features
        if functional_groups is not None:
            features += functional_groups
    return features

def bond_features(bond: Chem.rdchem.Bond) -> List[Union[bool, int, float]]:
    """
    Builds a feature vector for a bond.

    :param bond: An RDKit bond.
    :return: A list containing the bond features.
    """
    if bond is None:
        fbond = [1] + [0] * (BOND_FDIM - 1)
    else:
        bt = bond.GetBondType()
        fbond = [
            0, #bond is not None
            bt == Chem.rdchem.BondType.SINGLE,
            bt == Chem.rdchem.BondType.DOUBLE,
            bt == Chem.rdchem.BondType.TRIPLE,
            bt == Chem.rdchem.BondType.AROMATIC,
            (bond.GetIsConjugated() if bt is not None else 0),
            (bond.IsInRing() if bt is not None else 0)
        ]
        fbond += onek_encoding_unk(int(bond.GetStereo()), list(range(6)))
    return fbond

def map_reac_to_prod(mol_reac: Chem.Mol, mol_prod: Chem.Mol):
    """
    Build a dictionary of mapping atom indices in reactants to the products
    :param mol_reac: An RDKit molecule of the reactants
    :param mol_prod: An RDKit molecule of the products.
    :return: A dictionary of corresponding reactant + product atom indices.
    """
    only_prod_ids = []
    prod_map_to_id = {}
    mapnos_reac = set([atom.GetAtomMapNum() for atom in mol_reac.GetAtoms()])
    for atom in mol_prod.GetAtoms():
        mapno = atom.GetAtomMapNum()
        if mapno > 0:
            prod_map_to_id[mapno] = atom.GetIdx()
            if mapno not in mapnos_reac:
                only_prod_ids.append(atom.GetIdx())
        else:
            only_prod_ids.append(atom.GetIdx())
    only_reac_ids = []
    reac_id_to_prod_id = {}
    for atom in mol_reac.GetAtoms():
        mapno = atom.GetAtomMapNum()
        if mapno > 0:
            try:
                reac_id_to_prod_id[atom.GetIdx()] = prod_map_to_id[mapno]
            except KeyError:
                only_reac_ids.append(atom.GetIdx())
            else:
                only_reac_ids.append(atom.GetIdx())
        return reac_id_to_prod_id, only_prod_ids, only_reac_ids

class MolGraph:
    """
    A :class: `MolGraph` represents the graph structure + featurization of a single molecule

    A MolGraph computes the following attributes:
    * :code:`n_atoms`: number of atoms in molecule
    * :code:`n_bonds`: number of bonds in molecule.
    * :code:`f_atoms`: mapping from atom index to list of atom features
    * :code:`f_bonds`: mapping from bond index to list of bond features
    * :code:`a2b`: mapping from atom index to list of incoming bond indices
    * :code:`b2a`: mapping from bond index to index of atom bond originates from
    * :code:`b2revb`: mapping from bond index to index of reverse bond
    * :code:`overwrite_default_atom_features`: boolean to overwrite default atom descriptors
    * :code: `overwrite_default_bond_features`: boolean to overwrite default bond descriptors
    """

    def __init__(self, mol: Union[str, Chem.Mol, Tuple[Chem.Mol, Chem.Mol]],
                 atom_features_extra: np.ndarray = None,
                 bond_features_extra: np.ndarray = None,
                 overwrite_default_atom_features: bool = False,
                 overwrite_default_bond_features: bool = False):
        """
        :param mol: A SMILES or an RDKit molecule.
        :param atom_features_extra: a list of 20 numpy array containing additional atom features to featurize the molecule
        :param bond_features_extra: a list of 20 numpy arrays containing additional bond features to featurize the molecule
        :param overwrite_default_atom_features: boolean to overwrite default atom features by atom_features instead of concatenating
        :param overwrite_default_bond_features: boolean to overwrite default bond features by bond_features instead of concatenating
        """
        self.is_reaction = is_reaction()
        self.is_explicit_h = is_explicit_h()
        self.reaction_mode = reaction_mode()

        # convert SMILES to RDKit molecule if necessary
        if type(mol) == str:
            if self.is_reaction:
                mol = (make_mol(mol.split(">")[0], self.is_explicit_h), make_mol(mol.split(">")[-1], self.is_explicit_h))
            else:
                mol = make_mol(mol, self.is_explicit_h)

        self.n_atoms = 0 # num atoms
        self.n_bonds = 0 #num bonds
        self.f_atoms = [] # mapping from atom index to atom features
        self.f_bonds = [] # mapping from bond index to concat(in_atom, bond) features
        self.a2b = [] # mapping from atom index to incoming bond indices
        self.b2a = [] # mapping from bond index to index of atom the bond is coming from
        self.b2revb = [] # mapping from bond index to index of reverse bond
        self.overwrite_default_atom_features = overwrite_default_atom_features
        self.overwrite_default_bond_features = overwrite_default_bond_features

        if not self.isreaction:
            # Get atom features
            self.f_atoms = [atom_features(atom) for atom in mol.GetAtoms()]
            if atom_features_extra is not None:
                if overwrite_default_atom_features:
                    self.f_atoms = [descs.tolist() for descs in atom_features_extra]
                else:
                    self.f_atoms = [f_atoms + descs.tolist() for f_atoms, descs in zip(self.f_atoms, atom_features_extra)]

            self.n_atoms = len(self.f_atoms)
            if atom_features_extra is not None and len(atom_features_extra) != self.n_atoms:
                raise ValueError(f'The number of atoms in {Chem.MolToSmiles(mol)} is different from the length of the extra atom features')

            # initialize atom to bond mapping for each atom
            for _ in range(self.n_atoms):
                self.a2b.append([])

            # get bond features
            for a1 in range(self.n_atoms):
                for a2 in range(a1 + 1, self.n_atoms):
                    bond = mol.GetBondBetweenAtoms(a1, a2)

                    if bond is None:
                        continue

                    f_bond = bond_features(bond)
                    if bond_features_extra is not None:
                        descr = bond_features_extra[bond.GetIdx()].tolist()
                        if overwrite_default_bond_features:
                            f_bond = descr
                        else:
                            f_bond = descr
                    self.f_bonds.append(self.f_atoms[a1] + f_bond)
                    self.f_bonds.append(self.f_atoms[a2] + f_bond)

                    # update index mappings
                    b1 = self.n_bonds
                    b2 = b1 + 1
                    self.a2b[a2].append(b1)
                    self.b2a.append(a1)
                    self.a2b[a1].append(b2)
                    self.b2a.append(a2)
                    self.b2revb.append(b2)
                    self.b2revb.append(b1)
                    self.n_bonds += 2
            if bond_features_extra is not None and len(bond_features_extra) != self.n_bonds /2:
                raise ValueError(f'The number of bonds in {Chem.MolToSmiles(mol)} is different from the length of '
                                 f'the extra bond features')
        else: # reaction mode
            if atom_features_extra is not None:
                raise NotImplementedError('Extra atom features are currently not supported for reactions')
            if bond_features_extra is not None:
                raise NotImplementedError('Extra bond features are currently not supported for reactions')

            mol_reac = mol[0]
            mol_prod = mol[1]
            ri2pi, pio, rio = map_reac_to_prod(mol_reac, mol_prod)

            # get atom features
            f_atoms_reac = [atom_features(atom) for atom in mol_reac.GetAtoms()] + [atom_features(None) for index in pio]
            f_atoms_prod = [atom_features(mol_prod.GetAtomWithIdx(ri2pi[atom.GetIdx()])) if atom.GetIdx() not in rio else
                            atom_features(None) for atom in mol_reac.GetAtoms()] + [atom_features(mol_prod.GetAtomWithIdx(index)) for index in pio]

            if self.reaction_mode in ['reac_diff', 'prod_diff']:
                f_atoms_diff = [list(map(lambda x,y: x - y, ii, jj)) for ii, jj in zip(f_atoms_prod, f_atoms_reac)]
            if self.reaction_mode == 'reac_prod':
                self.f_atoms = [x+y[MAX_ATOMIC_NUM+1:] for x,y in zip(f_atoms_reac, f_atoms_prod)]
            elif self.reaction_mode == 'reac_diff':
                self.f_atoms = [x+y[MAX_ATOMIC_NUM+1:] for x,y in zip(f_atoms_reac, f_atoms_diff)]
            elif self.reaction_mode == 'prod_diff':
                self.f_atoms = [x+y[MAX_ATOMIC_NUM+1:] for x,y in zip(f_atoms_prod, f_atoms_diff)]
            self.n_atoms = len(self.f_atoms)
            n_atoms_reac = mol_reac.GetNumAtoms()

            # initialize atom to bond mapping for each atom
            for _ in range(self.n_atoms):
                self.a2b.append([])

            # get bond features
            for a1 in range(self.n_atoms):
                for a2 in range(a1 + 1, self.n_atoms):
                    if a1 >= n_atoms_reac and a2 >= n_atoms_reac: # both atoms only in product
                        bond_reac = None
                        bond_prod = mol_prod.GetBondBetweenAtoms(pio[a1 - n_atoms_reac], pio[a2 - n_atoms_reac])
                    elif a1 < n_atoms_reac and a2 >= n_atoms_reac: # one atom only in product
                        bond_reac = None
                        if a1 in ri2pi.keys():
                            bond_prod = mol_prod.GetBondBetweenAtoms(ri2pi[a1], pio[a2 - n_atoms_reac])
                        else:
                            bond_prod = None # atom only in reactant, other only in product
                    else:
                        bond_reac = mol_reac.GetBondBetweenAtoms(a1, a2)
                        if a1 in ri2pi.keys() and a2 in ri2pi.keys():
                            bond_prod = mol_prod.GetBondBetweenAtoms(ri2pi[a1], ri2pi[a2]) # both atoms in both reactants + products
                        else:
                            bond_prod = None # one or both atoms only in reactant
                    if bond_reac is None and bond_prod is None:
                        continue

                    f_bond_reac = bond_features(bond_reac)
                    f_bond_prod = bond_features(bond_prod)
                    if self.reaction_mode in ['reac_diff', 'prod_diff']:
                        f_bond_diff = [y - x for x, y in zip(f_bond_reac, f_bond_prod)]
                    if self.reaction_mode == 'reac_prod':
                        f_bond = f_bond_reac + f_bond_prod
                    elif self.reaction_mode == 'reac_diff':
                        f_bond = f_bond_reac + f_bond_diff
                    elif self.reaction_mode == 'prod_diff':
                        f_bond = f_bond_prod + f_bond_diff
                    self.f_bonds.append(self.f_atoms[a1] + f_bond)
                    self.f_bonds.append(self.f_atoms[a2] + f_bond)

                    # udpate index mappings
                    b1 = self.n_bonds
                    b2 = b1 + 1
                    self.a2b[a2].append(b1) # b1 = a1 --> a2
                    self.b2a.append(a1)
                    self.a2b[a1].append(b2)
                    self.b2a.append(a2)
                    self.b2revb.append(b2)
                    self.b2revb.append(b1)
                    self.n_bonds += 2

class BatchMolGraph:
    """
    A :class:`BatchMolGraph` represents the graph structure and featurization of a batch of molecules

    A BatchMolGraph contains the attributes of a :class:`MolGraph` plus:

    * :code:`atom_fdim`: dimensionality of atom feature vector.
    * :code:`bond_fdim`: dimensionality of bond feature vector (technically, combined atom/bond features)
    * :code:`a_scope`: list of tuples indicating start + end atom indices for each molecule
    * :code:`b_scope`: list of tuples indicating start + end bond indices for each molecule
    * :code:`max_num_bonds`: max num bonds neighboring an atom in this batch
    * :code:`b2b`: (Optional) mapping from bond index to incoming bond indices
    * :code:`a2a`: (Optional) mapping from atom index to neighboring atom indices
    """

    def __init__(self, mol_graphs: List[MolGraph]):
        r"""
        :param mol_graphs: a list of :class:`MolGraph`\s from which to construct the :class:`BatchMolGraph`
        """
        self.overwrite_default_atom_features =mol_graphs[0].overwrite_default_atom_features
        self.overwrite_default_bond_features = mol_graphs[0].overwrite_default_bond_features
        self.atom_fdim = get_atom_fdim(overwrite_default_atom = self.overwrite_default_atom_features)
        self.bond_fdim = get_bond_fdim(overwrite_default_bond = self.overwrite_default_bond_features,
                                       overwrite_default_atom = self.overwrite_default_atom_features)

        # start n_atoms and n_bonds at 1 b/c zero padding
        self.n_atoms = 1 # num atoms
        self.n_bonds = 1 # num bonds
        self.a_scope = [] # list of tuples indicating (start_atom_index, num_atoms) for each molecule
        self.b_scope = [] # list of tuples indicating (start_bond_index, num_bonds) for each molecule

        # all start with zero padding so that indexing with zero padding returns zeros
        f_atoms = [[0] * self.atom_fdim]
        f_bonds = [[0] * self.bond_fdim]
        a2b = [[]] # mapping from atom index to incoming bond indices
        b2a = [0] # mapping from bond index to index of atom bond is coming from
        b2revb = [0] # mapping from bond index to index of reverse bond

        for mol_graph in mol_graphs:
            f_atoms.extend(mol_graph.f_atoms)
            f_bonds.extend(mol_graph.f_bonds)

            for a in range(mol_graph.n_atoms):
                a2b.append([b + self.n_bonds for b in mol_graph.a2b[a]])

            for b in range(mol_graph.n_bonds):
                b2a.append(self.n_atoms + mol_graph.b2a[b])
                b2revb.append(self.n_bonds + mol_graph.b2revb[b])

            self.a_scope.append((self.n_atoms, mol_graph.n_atoms))
            self.b_scope.append((self.n_bonds, mol_graph.n_bonds))
            self.n_atoms += mol_graph.n_atoms
            self.n_bonds += mol_graph.n_bonds

        self.max_num_bonds = max(1, max(
            len(in_bonds) for in_bonds in a2b)) # max with 1 to fix a crash in rare case of all single-heavy-atom mols

        self.f_atoms = torch.FloatTensor(f_atoms)
        self.f_bonds = torch.FloatTensor(f_bonds)
        self.a2b = torch.LongTensor([a2b[a] + [0]*(self.max_num_bonds - len(a2b[a]) for a in range(self.n_atoms))])
        self.b2a = torch.LongTensor(b2a)
        self.b2revb = torch.LongTensor(b2revb)
        self.b2b = None # try to avoid computing b2b b/c O(n_atoms^3)
        self.a2a = None # only needed if using atom messages

    def get_components(self, atom_messages: bool = False) -> Tuple[torch.FloatTensor, torch.FloatTensor, torch.LongTensor,
                                                                    torch.LongTensor, torch.LongTensor, List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Returns the components of the :class:`BatchMolGraph`
        The returned components are, in order:
        * :code:`f_atoms`
        * :code:`f_bonds`
        * :code:`a2b`
        * :code:`b2a`
        * :code:`b2revb`
        * :code:`a_scope`
        * :code:`b_scope`

        :param atom_messages: whether to use atom messages instead of bond messages, if true, then bond feature
        vector will only contain bond features rather than both
        :return: a tuple with pytorch tensors with atom features, bond features, graph structure, and scope of atoms + bonds
        """
        if atom_messages:
            f_bonds = self.f_bonds[:, -get_bond_fdim(atom_messages = atom_messages,
                                                     overwrite_default_atom=self.overwrite_default_atom_features,
                                                     overwrite_default_bond=self.overwrite_default_bond_features):]
        else:
            f_bonds = self.f_bonds

        return self.f_atoms, f_bonds, self.a2b, self.b2a, self.b2revb, self.a_scope, self.b_scope

    def get_b2b(self) -> torch.LongTensor:
        """
        Computes (if necessary) + returns mapping from each bond index to all incoming bond indices
        :return: pytorch tensor with mapping from each bond index to all incoming bond indices
        """
        if self.b2b is None:
            b2b = self.a2b[self.b2a] # num_bonds * max_num_bonds
            # b2b includes reverse edge fore ach bond so need to mask out
            revmask = (b2b != self.b2revb.unsqueeze(1).repeat(1, b2b.size(1))).long() #num_bonds * max_num_bonds
            self.b2b = b2b * revmask

        return self.b2b

    def get_a2a(self) -> torch.LongTensor:
        """
        Computes if necessary + returns mapping from each atom index to all neighboring atom indices
        :return: pytorch tensor with mapping from each bond index to all incoming bond indices
        """
        if self.a2a is None:
            # b = a1 --> a2
            # a2b maps a2 to all incoming bonds b
            # b2a maps each bond b to the atom it comes from a1
            # thus b2a[a2b] maps atom a2 to neighboring atoms a1
            self.a2a = self.b2a[self.a2b] # num_atoms * max_num_bonds
        return self.a2a

def mol2graph(mols: Union[List[str], List[Chem.Mol], List[Tuple[Chem.Mol, Chem.Mol]]],
              atom_features_batch: List[np.array] = (None,),
              bond_features_batch: List[np.array] = (None,),
              overwrite_default_atom_features: bool = False,
              overwrite_default_bond_features: bool = False
              ) -> BatchMolGraph:
    """
    Converts list of SMILES or RDKit molecules to a :class:`BatchMolGraph` containing batch of molecular graphs
    :param mols: A list of SMILES or list of RDKit molecules
    :param atom_features_batch: list of 2D numpy arrays containing additional atom features to featurize the molecule
    :param bond_features_batch: list of 2D numpy array containing additional bond features to featurize the molecule
    :param overwrite_default_atom_features: boolean to overwrite default atom descriptors by atom_descriptors instead of concatenating
    :param overwrite_default_bond_features: boolean to overwrite default bond descriptors by bond_descriptors instead of concatenating
    :return: A :class:`BatchMolGraph` containing the combined molecular graph for the molecules
    """
    return BatchMolGraph([MolGraph(mol, af, bf,
                                   overwrite_default_atom_features=overwrite_default_atom_features,
                                   overwrite_default_bond_features=overwrite_default_bond_features)
                          for mol, af, bf
                          in zip_longest(mols, atom_features_batch, bond_features_batch)])




