from rdkit import Chem

def make_mol(s: str, keep_h: bool):
    """
    Builds an RDKit molecule from a SMILES string
    :param s: SMILES string
    :param keep_h: Boolean whether to keep hydrogens in input smiles, does not add hydrogens, only keeps if are specified
    :return: RDKit molecule
    """

    if keep_h:
        mol = Chem.MolFromSmiles(s, sanitize=False)
        Chem.SanitizeMol(mol, sanitizeOps=Chem.SanitizeFlags.SANITIZE_ALL^Chem.SanitizeFlags.SANITIZE_ADJUSTHS)
    else:
        mol = Chem.MolFromSmiles(s)
    return mol
