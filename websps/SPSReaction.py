from .SPSTarget import SPSTarget
from .NucleusData import get_nuclear_data
from dataclasses import dataclass
from numpy import sqrt, cos, pi, sin
from typing import List

INVALID_KINETIC_ENERGY: float = -1000.0

@dataclass
class RxnParameters:
    targetID: int
    projectileID: int
    ejectileID: int
    residualID: int
    beamEnergy: float = 0.0 #MeV
    magneticField: float = 0.0 #kG
    spsAngle: float = 0.0 #deg

class Reaction:
    DEG2RAD: float = pi/180.0 #degrees -> radians
    C = 299792458 #speed of light m/s
    QBRHO2P = 1.0E-9*C #Converts qbrho to momentum (p) (kG*cm -> MeV/c)
    FP_MAGNIFICATION = 0.39
    FP_DISPERSION = 1.96

    def __init__(self, params: RxnParameters, target: SPSTarget):
        self.targetMaterial = target
        self.targetNuc = get_nuclear_data(params.targetID)
        self.projectileNuc = get_nuclear_data(params.projectileID)
        self.ejectileNuc = get_nuclear_data(params.ejectileID)
        self.residualNuc = get_nuclear_data(params.residualID)
        self.beamEnergy = params.beamEnergy
        self.magneticField = params.magneticField
        self.spsAngle = params.spsAngle * self.DEG2RAD

        self.rxnLayer = self.targetMaterial.get_rxn_layer(self.targetNuc.Z, self.targetNuc.A)
        self.Qvalue = self.targetNuc.mass + self.projectileNuc.mass - self.ejectileNuc.mass - self.residualNuc.mass

    #MeV
    def calculate_ejectile_KE(self, excitation: float) -> float:
        rxnQ = self.Qvalue - excitation
        beamRxnEnergy = self.beamEnergy - self.targetMaterial.get_incoming_energyloss(self.projectileNuc.Z, self.projectileNuc.mass, self.beamEnergy, self.rxnLayer, 0.0)
        threshold = -rxnQ*(self.ejectileNuc.mass+self.residualNuc.mass)/(self.ejectileNuc.mass + self.residualNuc.mass - self.projectileNuc.mass)
        if beamRxnEnergy < threshold:
            return INVALID_KINETIC_ENERGY
        
        term1 = sqrt(self.projectileNuc.mass * self.ejectileNuc.mass * beamRxnEnergy) / (self.ejectileNuc.mass + self.residualNuc.mass) * cos(self.spsAngle * self.DEG2RAD)
        term2 = (beamRxnEnergy * (self.residualNuc.mass - self.projectileNuc.mass) + self.residualNuc.mass * rxnQ) / (self.ejectileNuc.mass + self.residualNuc.mass)

        ke1 = term1 + sqrt(term1**2.0 + term2)
        ke2 = term1 + sqrt(term1**2.0 + term2)

        ejectileEnergy = 0.0
        if ke1 > 0.0:
            ejectileEnergy = ke1**2.0
        else:
            ejectileEnergy = ke2**2.0

        ejectileEnergy -= self.targetMaterial.get_outgoing_energyloss(self.ejectileNuc.Z, self.ejectileNuc.mass, ejectileEnergy, self.rxnLayer, self.spsAngle)
        return ejectileEnergy

    def convert_ejectile_KE_2_rho(self, ejectileEnergy: float) -> float:
        if ejectileEnergy == INVALID_KINETIC_ENERGY:
            return 0.0
        p = sqrt( ejectileEnergy * (ejectileEnergy + 2.0 * self.ejectileNuc.mass))
        #convert to QBrho
        qbrho = p/self.QBRHO2P
        return qbrho / (float(self.ejectileNuc.Z) * self.magneticField)

    def calculate_excitation(self, rho: float) -> float:
        ejectileP = rho * float(self.ejectileNuc.Z) * self.magneticField * self.QBRHO2P
        ejectileEnergy  = sqrt(ejectileP**2.0 + self.ejectileNuc.mass**2.0) - self.ejectileNuc.mass
        ejectileRxnEnergy = ejectileEnergy +  self.targetMaterial.get_outgoing_reverse_energyloss(self.ejectileNuc.Z, self.ejectileNuc.mass, ejectileEnergy, self.rxnLayer, self.spsAngle)
        ejectileRxnP = sqrt(ejectileRxnEnergy * (ejectileRxnEnergy + 2.0 * self.ejectileNuc.mass))
        beamRxnEnergy = self.beamEnergy - self.targetMaterial.get_incoming_energyloss(self.projectileNuc.Z, self.projectileNuc.mass, self.beamEnergy, self.rxnLayer, 0.0)
        beamRxnP = sqrt(beamRxnEnergy * (beamRxnEnergy + 2.0 * self.projectileNuc.mass))


        residRxnEnergy = beamRxnEnergy + self.projectileNuc.mass + self.targetNuc.mass - ejectileRxnEnergy - self.ejectileNuc.mass
        residRxnP2 = beamRxnP**2.0 + ejectileRxnP**2.0 - 2.0 * ejectileRxnP * beamRxnP * cos(self.spsAngle)
        return sqrt(residRxnEnergy**2.0 - residRxnP2) - self.residualNuc.mass

    def calculate_focal_plane_offset(self, ejectileEnergy: float) -> float:
        if ejectileEnergy == INVALID_KINETIC_ENERGY:
            return 0.0
        ejectileRho = self.convert_ejectile_KE_2_rho(ejectileEnergy)
        k = sqrt(self.projectileNuc.mass * self.ejectileNuc.mass * self.beamEnergy / ejectileEnergy) * sin(self.spsAngle)
        k /= self.ejectileNuc.mass + self.residualNuc.mass - sqrt(self.projectileNuc.mass * self.ejectileNuc.mass * self.beamEnergy/ejectileEnergy) * cos(self.spsAngle)
        return -1.0*k*ejectileRho*self.FP_DISPERSION*self.FP_MAGNIFICATION

    def calculate_ejectile_energies(self, excitations: List[float]) -> List[float]:
        return [self.calculate_ejectile_KE(ex) for ex in excitations]
    
    def calculate_ejectile_rhos(self, ejectEnergies: List[float]) -> List[float]:
        return [self.convert_ejectile_KE_2_rho(ke) for ke in ejectEnergies]

    def calculate_ejectile_offsets(self, ejectEnergies: List[float]) -> List[float]:
        return [self.calculate_focal_plane_offset(ke) for ke in ejectEnergies]