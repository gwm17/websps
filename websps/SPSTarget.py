import pycatima as catima
from dataclasses import dataclass, field
from numpy import pi, cos, uint32
from .NucleusData import construct_catima_layer_element
from .db import get_nucleus_id

INVALID_RXN_LAYER: int = -1
ADAPTIVE_DEPTH_MAX: int = 100
ENERGY_PERCENT_STEP_MIN: float = 0.001

@dataclass
class TargetLayer:
    compound_list: list[tuple[uint32 , int]] = field(default_factory=list) #nucleus id, Stoichiometry
    thickness: float = 0.0 #ug/cm^2

#integrate energy loss starting from the final energy and running backwards to initial energy
#catima does not natively provide this type of method
#returns the total energy loss (really in this case energy gain) through the material
def get_reverse_energyloss(projectile: catima.Projectile, material: catima.Material) -> float:
    depth = 0
    e_out = projectile.T() #MeV/u
    e_initial = e_out
    x_step = 0.25*material.thickness() #g/cm^2
    x_traversed = 0.0
    e_step = catima.dedx(projectile, material)*x_step
    A_recip = 1.0/projectile.A()

    if material.thickness() <= 0.0:
        return 0.0
    
    #The integration step is adaptive, so use while(true)
    while(True):

        if e_step/e_initial > ENERGY_PERCENT_STEP_MIN and depth < ADAPTIVE_DEPTH_MAX:
            depth += 1
            x_step *= 0.5
            e_step = catima.dedx(projectile, material)*x_step*A_recip

        elif (x_step + x_traversed) >= material.thickness():
            x_step = material.thickness() -  x_traversed
            e_step = catima.dedx(projectile, material)*x_step
            e_initial += e_step*A_recip
            projectile.T(e_initial)
            return (e_initial - e_out)*projectile.A()

        elif depth == ADAPTIVE_DEPTH_MAX:
            return e_out*projectile.A()
        else:
            e_step = catima.dedx(projectile, material)*x_step
            e_initial += e_step*A_recip
            projectile.T(e_initial)
            x_traversed += x_step

#integrate energy loss starting from the initial energy to final energy
#catima does not natively provide this type of method, only a calculate function which does a whole bunch of other stuff too
#returns the total energy loss through the material
def get_energyloss(projectile: catima.Projectile, material: catima.Material) -> float:
    depth = 0
    e_in = projectile.T() # MeV/u
    e_final = e_in
    x_step = 0.25*material.thickness() #g/cm^2
    x_traversed = 0.0
    e_step = catima.dedx(projectile, material)*x_step
    A_recip = 1.0/projectile.A()

    if material.thickness() <= 0.0:
        return 0.0

    while(True):
    
        if e_step/e_final > ENERGY_PERCENT_STEP_MIN and depth < ADAPTIVE_DEPTH_MAX:
            depth += 1
            x_step *= 0.5
            e_step = catima.dedx(projectile, material)*x_step*A_recip
        
        elif (x_step + x_traversed) >= material.thickness():
            x_step = material.thickness() - x_traversed
            e_step = catima.dedx(projectile, material)*x_step*A_recip
            e_final -= e_step
            projectile.T(e_final)
            return (e_in - e_final)*projectile.A()
        
        elif depth == ADAPTIVE_DEPTH_MAX:
            return e_in*projectile.A()
        
        else:
            e_step = catima.dedx(projectile, material)*x_step*A_recip
            e_final -= e_step
            projectile.T(e_final)
            x_traversed += x_step
        
class SPSTarget:
    UG2G: float = 1.0e-6 #convert ug to g
    def __init__(self, layers: list[TargetLayer], name: str = "default"):
        self.layer_details = layers
        self.name = name

    def __str__(self):
        return self.name

    def get_rxn_layer(self, zt: int, at: int) -> int:
        tID = get_nucleus_id(zt, at)
        for idx, layer in enumerate(self.layer_details):
            for (id, s) in layer.compound_list:
                if id == tID:
                    return idx
        return INVALID_RXN_LAYER

    #Calculate energy loss for a particle coming into the target, up to rxn layer (halfway through rxn layer)
    def get_incoming_energyloss(self, zp: int, ap: float, e_initial: float, rxn_layer: int, angle: float) -> float:
        if angle == pi*0.5:
            return e_initial

        projectile = catima.Projectile(zp, ap)
        e_current = e_initial/ap

        for (idx, layer) in enumerate(self.layer_details):
            material = catima.Material([construct_catima_layer_element(id, s) for (id, s) in layer.compound_list])
            projectile.T(e_current) #catima wants MeV/u
            if idx == rxn_layer:
                material.thickness(self.layer_details[idx].thickness * self.UG2G / (2.0 * abs(cos(angle))))
                e_current -= get_energyloss(projectile, material)
                return e_initial - e_current*ap
            else:
                material.thickness(self.layer_details[idx].thickness * self.UG2G / abs(cos(angle)))
                e_current -= get_energyloss(projectile, material)

        return e_initial - e_current*ap

    #Calculate energy loss for a particle leaving the target, from rxn layer (halfway through rxn layer) to end
    def get_outgoing_energyloss(self, zp: int, ap: float, e_initial: float, rxn_layer: int, angle: float) -> float:
        if angle == pi*0.5:
            return e_initial

        projectile = catima.Projectile(zp, ap)
        e_current = e_initial/ap

        for (idx, layer) in enumerate(self.layer_details[rxn_layer:], start=rxn_layer):
            material = catima.Material([construct_catima_layer_element(id, s) for (id, s) in layer.compound_list])
            projectile.T(e_current) #catima wants MeV/u
            if idx == rxn_layer:
                material.thickness(self.layer_details[idx].thickness * self.UG2G / (2.0 * abs(cos(angle))))
            else:
                material.thickness(self.layer_details[idx].thickness * self.UG2G / abs(cos(angle)))
            e_current -= get_energyloss(projectile, material)

        return e_initial - e_current*ap

    #Calculate reverse energy loss (energy gain) for a particle that left the target after a reaction (end -> rxn_layer)
    def get_outgoing_reverse_energyloss(self, zp: int, ap: float, e_final: float, rxn_layer: int, angle: float) -> float:
        if angle == pi*0.5:
            return 0.0

        projectile = catima.Projectile(zp, ap)
        e_current = e_final/ap
        sublist = self.layer_details[rxn_layer:] #only care about rxn_layer -> exit
        reveresedRxnLayer = len(sublist) -1 #when reversed rxn_layer is the last layer
        for (idx, layer) in reversed(list(enumerate(sublist))):
            material = catima.Material([construct_catima_layer_element(id, s) for (id, s) in layer.compound_list])
            projectile.T(e_current) #catima wants MeV/u
            if idx == reveresedRxnLayer:
                material.thickness(self.layer_details[idx].thickness * self.UG2G / (2.0 * abs(cos(angle))))
            else:
                material.thickness(self.layer_details[idx].thickness * self.UG2G / abs(cos(angle)))
            e_current += get_reverse_energyloss(projectile, material)

        return e_current*ap - e_final