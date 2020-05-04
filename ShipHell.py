
from pyglet import image
from pyglet.gl import *
from pyglet.window import key
from pyglet.window import mouse

import os, math, random, threading, itertools

from lepton import Particle, ParticleGroup, default_system, ParticleSystem
from lepton.particle_struct import Vec3
from lepton.renderer import BillboardRenderer
from lepton.texturizer import SpriteTexturizer
from lepton.emitter import StaticEmitter, PerParticleEmitter
from lepton.controller import Movement, Magnet, Collector, Lifetime, Fader, Growth
from lepton.domain import Sphere, Point


d3 = True
trails = True
dothreads = False
cameraOn = True
fullscreen = False
lazysearch = 15  # -1 to disable
trailSize = (1, 60)

inBattle = False

config = pyglet.gl.Config(double_buffer=True)
if fullscreen:
    win = pyglet.window.Window(resizable=True,
         visible=False, fullscreen=fullscreen)
else:
    win = pyglet.window.Window(640, 480, resizable=True,
         visible=False, fullscreen=False)
win.set_vsync = False
win.clear()

glEnable(GL_BLEND)
glEnable(GL_POINT_SMOOTH)
glShadeModel(GL_SMOOTH)
glBlendFunc(GL_SRC_ALPHA, GL_ONE)
glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
glDisable(GL_DEPTH_TEST)


def resize(widthWindow, heightWindow):
    glViewport(0, 0, widthWindow, heightWindow)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(70, 1.0 * widthWindow / heightWindow, 0.001, 10000.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

win.on_resize = resize

texture = image.load(os.path.join(os.path.dirname(__file__),
    'flare3.png')).get_texture()
texturizer = SpriteTexturizer(texture.id)
texture2 = image.load(os.path.join(os.path.dirname(__file__),
    'dot1.png')).get_texture()
texturizer2 = SpriteTexturizer(texture2.id)

controls = {'fw': False, 'bk': False, 'lf': False, 'rt': False, 'f1': False,
    'f2': False, 'strl': False, 'strr': False, 'act1': False, 'act2': False}

###


class stratMap(object):

    def __init__(self):
        self.sides = {}
        self.fleets = {}
        self.regions = {}
        self.startRegions()
        pyglet.clock.schedule_interval(self.loop, (1.0 / 30.0))
#        self.loop()

    def startRegions(self):
        for i in range(10):
            xx = random.randrange(-500, 500)
            yy = random.randrange(-500, 500)
            zz = random.randrange(-500, 500)
            size = random.randrange(5, 10)
            reg = {i: {'x': xx, 'y': yy, 'z': zz, 'side': -1, 'size': size}}
            self.regions.update(reg)
        # TEST FLEETS
        f1 = {0: {'side': 1, 'pos': (0, 0, 0), 'data': {'quick': 50, 'arrow':30, 'terminator': 8, 'hammer': 0, 'deathstar': 6}}}
        f2 = {1: {'side': 2, 'pos': (0, 0, 0), 'data': {'quick': 0, 'standard': 50, 'sam': 3, 'deathstar': 0, 'mooncruiser': 1}}}
        self.createFleet(f1)
        self.createFleet(f2)

    def postBattle(self, data):
        self.loadMap()
        pyglet.clock.schedule_interval(self.loop, (1.0 / 30.0))

    def removeFleet(self, fleet):
        del(self.fleets[fleet])

    def createFleet(self, fleet):
        self.fleets.update(fleet)
        #print self.fleets

    def updateFleet(self, fleet, newfleet):
        if len(newfleet) == 0:
            self.removeFleet(fleet)
        else:
            self.fleets[fleet] = newfleet

    def saveMap(self):
        pass

    def loadMap(self):
        pass

    def loop(self, dt):
        pyglet.clock.unschedule(self.loop)
        if True:  # here be conditions for battle e.g. fleets colliding
            self.saveMap()
            self.New_Map(self.fleets[0], self.fleets[1])

    def New_Map(self, fleet1, fleet2):
        global yrot, xrot, ytra, xtra, ztra, camera, ships, battle, inBattle
        inBattle = True
        ships = []
        yrot = 0.0
        xrot = 0.0
        ytra = 1.0
        xtra = 0.0
        ztra = -500

        camera = Camera((xrot, yrot, ztra), scale=5)
        battle = Battle(strat, fleet1, fleet2)
        battle.LoadShips()
        #battle.Battle1()
        battle.Battle()
        if dothreads:
            ThreadMoveBola().start()
            ThreadSystemUpdate().start()
        else:
            pyglet.clock.schedule_interval(moveBola, (1.0 / 30.0))
            pyglet.clock.schedule_interval(default_system.update, (1.0 / 100.0))


class Camera(object):

    def __init__(self, position, scale=1, angle=0):
        self.x, self.y, self.z = position
        self.angle = angle
        self.scale = scale

    def focus(self, win_width, win_height, tx, ty, tz):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = (win_width * 1.04) / (win_height + 1)
        #gluOrtho2D(-self.scale * aspect, + self.scale * aspect, -self.scale, self.scale)
        gluPerspective(90, aspect, 1, 10000)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.x, self.y, self.z + 1000, tx, ty, 0, 0, 1, 0)
#        gluLookAt(self.x, self.y, self.z, tx, 0, 0, math.sin(self.angle), math.cos(self.angle), 0.0)

    def setPosition(self, xx, yy, zz):
        self.x, self.y, self.z = xx, yy, zz


class Commander(object):

    def __init__(self, name="", side=-1):
        self.side = side
        self.name = name

    def getOrders(self, ship):
        t = ship
        min_dist = 9999999999999
        global ships  # should it be a parameter instead? check for aliasing
        for s in ships:
            if s.side != self.side:
                d = distance_to_ship(ship, s, squared=True) / (1 + s.size)  # the bigger, the better
                if d < min_dist:
                    t = s
                    min_dist = d
        return t


class SquadLeader(object):

    def __init__(self):
        self.leader = None


class ship(object):

    def __init__(self, x, y, z, r, side=-1, hp=50, controlable=False,
        weapon_range=5, dispersion=5, agility=50, weapon_base_damage=2,
        guidance=100, shortguide=0, partColor=(0.6,0.5,0.2,1), firerate=10,
        shots=1, vo=30, maxvel=10,ammoMaxvel=20, combatDistance=50, behavior=0,
        commander=None, multipleTargets=False, name="", ammoDamp=0.98):
        self.name = name
        self.domain = Sphere((x, y, z), r)  # a.center -> vector del centro , a.outer_radius -> radio externo , a.inner_radius -> radio interno
        self.size = r
        self.controller = Collector(self.domain, callback=self.contact)
        self.magnet = Magnet(self.domain, charge=guidance, exponent=shortguide)
        self.commander = commander
        self.mission = self.domain.center
        self.target = None
        self.alive = True
        self.targetMode = ['standard', 1]
        self.behavior = behavior  # 0:free 1: escort 2: slave
        self.hp = hp
        self.agility = agility
        self.maxvel = maxvel
        self.timer = {0: 0, 1: 2, 2: 0, 3: 0, 4: 0}  # timers placeholder
        self.counter = {0: 0, 1: 0}  # counters placeholder
        self.side = side
        self.combatDistance = combatDistance
        self.velocity = Vec3(0, 0, 0)
        self.multipleTargets = multipleTargets
        self.firerate = firerate
        self.weapon_base_damage = weapon_base_damage
        wbd = self.weapon_base_damage
        rr = r * 2
        self.dispersion = dispersion
        self.vo = vo
        self.ammoDamp = ammoDamp
        self.ammoMaxvel = ammoMaxvel
        self.shots = shots
        self.weapon_range = weapon_range
        self.xx = self.yy = self.zz = 0
        self.Objective = Sphere((0, 0, 0), 1)
        self.color = partColor  # (0.4,0.5,0.4,0.5)
        #self.prevController = Collector(self.domain)#DUMMY CONTROLLER
        self.controlable = controlable
        self.impacto = ParticleGroup(renderer=BillboardRenderer(texturizer),
            controllers=[
                Lifetime(1),
                Fader(fade_out_start=0, fade_out_end=1),
            ]
        )
        self.deathplosion = ParticleGroup(renderer=BillboardRenderer(texturizer),
            controllers=[
                Lifetime(self.size / 5 + 1),
                Fader(fade_out_start=0, fade_out_end=self.size / 5 + 1),
            ]
        )
        self.selector_emitter = StaticEmitter(
            template=Particle(
                position=(0, 0, 0),
                color=self.color,
            )
        )
        self.impacto_emitter = StaticEmitter(
            template=Particle(
                position=(0, 0, 0),
                color=(0.9, 0.8, 0.8),
            ),
            position=self.domain,
            #size=[(5, 5, 5), (10, 10, 10), (15, 15, 15)],
        )
        self.hull = ParticleGroup(renderer=BillboardRenderer(texturizer2),
            controllers=[
                Lifetime(100000),
                Movement(max_velocity=self.maxvel, damping=0.98),
                Magnet(self.Objective, charge=self.agility, exponent=0),
            ]
        )
        emiter = StaticEmitter(position=self.domain,
            template=Particle(color=self.color, size=(rr, rr, rr),))
        emiter.emit(1, self.hull)

        if trails:
            if maxvel / r >= 20:
                self.trail = ParticleGroup(
                    renderer=BillboardRenderer(texturizer2),
                    controllers=[
                        Lifetime(trailSize[0]),
                        Fader(fade_in_start=0, fade_in_end=0.1,
                            fade_out_start=0, fade_out_end=trailSize[0]),
                        Growth(-1 * r),
                        PerParticleEmitter(self.hull, rate=trailSize[1],
                        template=Particle(color=self.color,
                            size=(rr, rr, rr),)),
                    ]
                )

        self.ammo = ParticleGroup(renderer=BillboardRenderer(texturizer),
            controllers=[
                self.magnet,
                Movement(min_velocity=0, max_velocity=self.ammoMaxvel, damping=self.ammoDamp),
                Lifetime(self.weapon_range),
                Fader(fade_out_start=self.weapon_range - 1,
                fade_out_end=self.weapon_range),
            ]
        )

        self.weapon = PerParticleEmitter(self.hull,  # rate=self.firerate,
            template=Particle(
                velocity=self.velocity,  # fixed value
                position=(self.getPosition()),
                color=partColor,
            ),
            position=self.domain,
            size=[(wbd * 0.5, wbd * 0.5, wbd * 0.5), (wbd, wbd, wbd),
            (wbd * 1.5, wbd * 1.5, wbd * 1.5)],
            deviation=Particle(
                velocity=(self.dispersion, self.dispersion, self.dispersion * d3),
                rotation=(0, 0, math.pi / 6),
                #color=(0.05,0.05,0.05,0),
            )
        )

    def nearest_enemy(self, ships, min_dist=99999, side=-1, addCollectors=False, limit=10, lazy = lazysearch):
        colla = 0
        target = None
        min_dist **= 2
        colld = min_dist
        if self.targetMode[0] == 'custom':
            selfRadius = self.targetMode[1]
        else:
            selfRadius = self.size
        selfAmmo = self.ammo
        if lazy != -1:
            c = lazysearch
            for ship in ships:
                if colla < limit and c > 0:
                    if ship != self and ship.side != side:
                        #var = math.fabs(ship.size - selfRadius) + 0.1
                        #var = 1 if math.fabs(ship.domain.radius - selfRadius) < selfRadius else 5
                        var = 0.1 if math.fabs(ship.size - selfRadius) < selfRadius else 2
                        dist = distance_to_ship(self, ship, squared=True) * var
                        if addCollectors:
                            if dist < colld:
                                colla += 1
                                selfAmmo.bind_controller(*[ship.controller])
                        if dist < min_dist and c > 0:
                            c -= 1
                            target = ship
                            min_dist = dist
                else:
                    break
        else:
            for ship in ships:
                if colla < limit:
                    if ship != self and ship.side != side:
                        #var = math.fabs(ship.size - selfRadius) + 0.1
                        #var = 1 if math.fabs(ship.domain.radius - selfRadius) < selfRadius else 5
                        var = 0.1 if math.fabs(ship.size - selfRadius) < selfRadius else 2
                        dist = distance_to_ship(self, ship, squared=True) * var
                        if addCollectors:
                            if dist < colld:
                                colla += 1
                                selfAmmo.bind_controller(*[ship.controller])
                        if dist < min_dist:
                            target = ship
                            min_dist = dist
                else:
                    break
        return target

    def getPosition(self):
        return (self.domain.center[0], self.domain.center[1],
        self.domain.center[2])

    def getPositionVec3(self):
        return Vec3(self.domain.center[0], self.domain.center[1],
        self.domain.center[2])

    def contact(self, particle, group, bola):
        if self.hp > 0:
            #dam = math.ceil(particle.size[0] * (particle.color[0] + particle.color[1] + particle.color[2]))  # color-based damage
            dam = math.ceil(particle.size[0])
            self.hp -= dam
            self.impacto_emitter.template.position = self.getPosition()
            self.impacto_emitter.template.size = (dam,dam,dam)
            self.impacto_emitter.emit(1, self.impacto)
            if self.hp <= 0:
                self.color = (0.5, 0.1, 0.1)
                self.controlable = False
                self.destroy()

    def destroy(self, flag=True):  # flag = True if it has been destroyed in combat
        global trails
        self.alive = False
        for part in self.hull:  # remove hull particle
            self.hull.kill(part)
        if flag:  # if destroyed in combat, explode
            s = self.size
            ss = s * 10
            self.impacto_emitter.template.size = (ss,ss,ss)
            self.impacto_emitter.emit(int(2 * s + 1), self.deathplosion)
            ships.remove(self)
            battle.removeShip(self.side)

    def DirToTarget(self, target):
        direction = target.getPositionVec3() - self.getPositionVec3()
        direction = direction.normalize()
        return direction

    def targetManagement(self, ships):
        stimer = self.timer
        if stimer[2] <= 0:
            stimer[2] = random.randint(100, 500)
            if self.target == None or distance_to_ship(self, self.target, squared=True) > (self.weapon_range * self.ammoMaxvel * 1.5) ** 2:
                [self.ammo.unbind_controller(i) for i in self.ammo.controllers if i.__class__.__name__ == "Collector"]
                self.target = self.nearest_enemy(ships, side=self.side,
                    min_dist=self.weapon_range * self.ammoMaxvel * 1.5,
                    addCollectors=self.multipleTargets, lazy=False)
                if self.target and self.target.alive:
                    self.magnet.domain = self.target.domain
                    if not self.multipleTargets:
                        self.ammo.bind_controller(*[self.target.controller]) # NO COLLECTOR TEST
                if self.commander and self.target == None:
                    self.mission = self.commander.getOrders(self).domain.center
        if stimer[3] <= 0:
            stimer[3] = 30
            if self.target and not self.target.alive:  # targeting a dead ship
                self.target = None
                stimer[2] = 10
        if stimer[1] <= 0 and self.target:
            for part in self.hull:
                h = part
            d = self.DirToTarget(self.target)
            self.weapon.template.velocity = d * self.vo + h.velocity
            self.weapon.emit(self.shots, self.ammo)
        stimer[2] -= 1
        stimer[3] -= 1

    def moveAround(self, ships):
        timer = self.timer
        for part in self.hull:
            self.domain.center = part.position
        timer[1] -= 1
        if timer[1] < 0:
            timer[1] = self.firerate
        if not self.controlable:
            self.targetManagement(ships)
            if timer[0] <= 0:
                timer[0] = random.randint(100, 300)
                agg = int(self.combatDistance)
                self.counter[0] += 1
                if self.counter[0] == 3:
                    agg += 100
                    self.counter[0] = 0
                self.xx = random.randint(-agg, agg)
                self.yy = random.randint(-agg, agg)
                self.zz = random.randint(-agg, agg)
            if timer[4] <= 0:
                timer[4] = 2
                if self.target and self.target.alive:
                    stdc = self.target.domain.center
                    self.Objective.center[0] = stdc[0] + self.xx
                    self.Objective.center[1] = stdc[1] + self.yy
                    if d3:
                        self.Objective.center[2] = stdc[2] + self.zz
                else:
                    if self.commander:
                        pos = self.mission
                    else:
                        pos = self.domain.center
                    self.Objective.center[0] = pos[0] + self.xx
                    self.Objective.center[1] = pos[1] + self.yy
                    if d3:
                        self.Objective.center[2] = pos[2] + self.zz
            timer[0] -= 1
            timer[4] -= 1



class Battle:

    def __init__(self, stratmap, f1, f2):
        self.bandos = {}
        self.shipData = {}  # key = ship name, value = ship data
        self.commanders = []
        self.stratmap = stratmap
        self.f1 = f1
        self.f2 = f2

    def removeShip(self, side):
        self.bandos[side] -= 1
        if self.bandos[side] == 0:
            del self.bandos[side]
        if len(self.bandos) <= 1:
            pyglet.clock.unschedule(self.endbattle)  # prevent multiple calls
            pyglet.clock.schedule_once(self.endbattle, 3)

    def endbattle(self, dt):
        global battle, ships
        data = {}
        winnerside = -1
        while len(ships) > 0:
            for ship in ships:
                winnerside = ship.side
                if ship.name in data:
                    data[ship.name] += 1
                else:
                    a = {ship.name: 1}
                    data.update(a)
                ships.remove(ship)
                ship.destroy(flag=False)
        while len(default_system.groups) > 0:
            [default_system.remove_group(group) for group in default_system.groups]
        pyglet.clock.unschedule(moveBola)
        pyglet.clock.unschedule(default_system.update)
        self.stratmap.postBattle(data)
        print winnerside, data
#        battle = Battle()
#        battle.LoadShips()
#        battle.Battle1()

    def Battle(self):
        self.commanders = [
        Commander(side=1),
        Commander(side=2),
        Commander(side=3)]

        self.bandos = {1: 0, 2: 0}
        colors = {'magenta': (0.6, 0.1, 0.2, 1), 'dorado': (0.8, 0.5, 0.2, 1), 'cyan': (0.2, 0.6, 0.8, 1),'verde': (0.2, 0.6, 0.2, 1)}

        for ship in self.f1['data']:
            for j in range(self.f1['data'][ship]):
                size = self.shipData[ship]['size'] * 5
                self.bandos[1] += 1
                x = -550 + size * int(j / 50); y = j * size - (int(j / 50) - 1); z = 0
                self.createShip(ship, x, y, z, 1, colors['cyan'], self.commanders[0])

        for ship in self.f2['data']:
            for j in range(self.f2['data'][ship]):
                size = self.shipData[ship]['size'] * 5
                self.bandos[2] += 1
                x = 550 + size * int(j / 50); y = j * size - (int(j / 50) - 1); z = 0
                self.createShip(ship, x, y, z, 2, colors['magenta'], self.commanders[1])

    #def Battle1(self):
        #self.commanders = [
        #Commander(side=1),
        #Commander(side=2),
        #Commander(side=3)]

        #self.bandos = {1: 0, 2: 0}

        #for i in range(20):
            #self.bandos[1] += 1
            #x = -250 + 5 * int(i / 50); y = i * 5 - (int(i / 50) - 1) * 250; z = 0
            #self.createShip("sam", x, y, z, 1, (0.8, 0.5, 0.2, 1), self.commanders[0])

        #for i in range(50):
            #self.bandos[2] += 1
            #x = 250 + 5 * int(i / 50); y=i * 5 - (int(i / 50) - 1) * 250; z = 0
            #self.createShip("quick", x, y, z, 2, (0.6, 0.1, 0.2, 1), self.commanders[1])
        #for i in range(10):
            #self.bandos[2] += 1
            #x = 1250 + 5 * int(i / 50); y=i * 5 - (int(i / 50) - 1) * 250; z = 0
            #self.createShip("hammer", x, y, z, 2, (0.6, 0.1, 0.2, 1), self.commanders[1])

    def LoadShips(self):

        shipFile = open("ships.txt")  # ship database
        aship = {}  # to be filled with data
        for line in shipFile:
            if "name" in line:
                key = line[5:].rstrip().strip('""')
            if "size" in line:
                aship['size'] = (float(line.strip("size=")))
            if "hp" in line:
                aship['hp'] = (int(line.strip("hp=")))
            if "weapon_range" in line:
                aship['weapon_range'] = (float(line.strip("weapon_range=")))
            if "vo" in line:
                aship['vo'] = (float(line.strip("vo=")))
            if "agility" in line:
                aship['agility'] = (float(line.strip("agility=")))
            if "shots" in line:
                aship['shots'] = (int(line.strip("shots=")))
            if "dispersion" in line:
                aship['dispersion'] = (float(line.strip("dispersion=")))
            if "firerate" in line:
                aship['firerate'] = (int(line.strip("firerate=")))
            if "maxvel" in line:
                aship['maxvel'] = (float(line.strip("maxvel=")))
            if "ammoMaxvel" in line:
                aship['ammoMaxvel'] = (float(line.strip("ammoMaxvel=")))
            if "combatDistance" in line:
                aship['combatDistance'] = (float(line.strip("combatDistance=")))
            if "weapon_base_damage" in line:
                aship['weapon_base_damage'] = (int(line.strip("weapon_base_damage=")))
            if "guidance" in line:
                aship['guidance'] = (float(line.strip("guidance=")))
            if "shortguide" in line:
                aship['shortguide'] = (float(line.strip("shortguide=")))
            if "ammoDamp" in line:
                aship['ammoDamp'] = (float(line.strip("ammoDamp=")))
            if "shipend" in line:
                self.shipData.update({key: aship})  # load data to ship db
                aship ={ }  # reset for next iteration
        shipFile.close()

    def createShip(self, shipType, x, y, z, side, color, commander=None):
        nave = self.shipData[shipType]
        coso = ship(x, y, z, nave['size'], side=side, hp=nave['hp'],
        weapon_range=nave['weapon_range'], vo=nave['vo'], partColor=color,
        agility=nave['agility'], shots=nave['shots'],
        dispersion=nave['dispersion'], firerate=nave['firerate'],
        maxvel=nave['maxvel'], ammoMaxvel=nave['ammoMaxvel'],
        combatDistance=nave['combatDistance'],
        weapon_base_damage=nave['weapon_base_damage'],
        commander=commander, guidance=nave['guidance'],
        shortguide=nave['shortguide'], name=shipType, ammoDamp=nave['ammoDamp'])
        ships.append(coso)

###


def moveBola(dt=None):
    #bola = ships[len(ships) - 1]
    #if bola.controlable:
        #if controls['fw']:
            #bola.Objective.center[1] += 0.6
        #if controls['bk']:
            #bola.Objective.center[1] -= 0.6
        #if controls['rt']:
            #bola.Objective.center[0] += 0.6
        #if controls['lf']:
            #bola.Objective.center[0] -= 0.6
        #if controls['f1']:
            #bola.targetManagement(ships)
    [coso.moveAround(ships) for coso in ships]


def distance_to_ship(ship1, ship2, squared=False):
    s1 = ship1.domain.center
    s2 = ship2.domain.center
    if squared:
        return math.pow(s1[0] - s2[0], 2) + math.pow(s1[1] - s2[1], 2)
        + math.pow(s1[1] - s2[2], 2)
    else:
        return math.sqrt(math.pow(s1[0] - s2[0], 2) + math.pow(s1[1] - s2[1], 2)
         + math.pow(s1[1] - s2[2], 2))


def drawBola():
    global xtra, ytra, ztra
    glPointSize(20)
    glBegin(GL_POINTS)
    glColor3f(1, 1, 1)
    glVertex3f(-xtra, -ytra, ztra + 500)
    glEnd()


@win.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    if buttons == mouse.RIGHT:
        global xtra, ytra
        if d3:
            xtra += -dx
            ytra += -dy
        else:
            xtra -= dx * (-ztra) * 0.003
            ytra -= dy * (-ztra) * 0.003
    if buttons == mouse.LEFT:
        global yrot, xrot
        if d3:
            yrot += dx * 0.3
            xrot -= dy * 0.3


@win.event
def on_mouse_scroll(x, y, scroll_x, scroll_y):
    global ztra
    if d3:
        ztra += -scroll_y * 15
        if ztra < -999:
            ztra = -999
    else:
        ztra += scroll_y * ztra * 0.1
        if ztra > 0:
            ztra = 0

fps_display = pyglet.clock.ClockDisplay()
#pyglet.clock.set_fps_limit(30)


@win.event
def on_draw():
    global inBattle
    if inBattle:
        global i
        global yrot, xrot, ztra
        global camera
        win.clear()
        if cameraOn:
            camera.setPosition(xtra, ytra, ztra)
            camera.focus(win.width, win.height, xtra, ytra, ztra)
            glRotatef(yrot, 0.0, 1.0, 0.0)
            glRotatef(xrot, 1.0, 0.0, 0.0)
        else:  # Moves the world around the camera
            glLoadIdentity()
            glTranslatef(xtra, ytra, ztra)
            glRotatef(yrot, 0.0, 1.0, 0.0)
            glRotatef(xrot, 1.0, 0.0, 0.0)
    default_system.draw()
#    fps_display.draw()
#    drawBola()


@win.event
def on_key_press(symbol, modifiers):
    if symbol == key.BACKSPACE:  # reset camera position
        global xtra, ytra, ztra, selected
        xtra, ytra, ztra = 0, 0, -500
    if inBattle:  # only during a battle
        if symbol == key.PLUS or symbol == key.NUM_ADD:  # accelerate time
            pyglet.clock.schedule_interval(moveBola, (1.0 / 30.0))
            pyglet.clock.schedule_interval(default_system.update, (1.0 / 100.0))
        if symbol == key.MINUS or symbol == key.NUM_SUBTRACT:  # reset time
            pyglet.clock.unschedule(moveBola)
            pyglet.clock.unschedule(default_system.update)
            pyglet.clock.schedule_interval(default_system.update, (1.0 / 100.0))
            pyglet.clock.schedule_interval(moveBola, (1.0 / 30.0))
        if symbol == key.P:  # Pause
            pyglet.clock.unschedule(moveBola)
            pyglet.clock.unschedule(default_system.update)
        if symbol == key._1:
            selected = [ship for ship in ships if ship.side == 1 and ship.size < 2]
            print 'fighters selected: ', len(selected)
        if symbol == key._2:
            selected = [ship for ship in ships if ship.side == 1 and ship.size >= 2 and ship.size < 5]
            print 'destroyers selected: ', len(selected)
        if symbol == key._3:
            selected = [ship for ship in ships if ship.side == 1 and ship.size >= 5 ]
            print 'cruisers selected: ', len(selected)
        if symbol == key.Q:
            print 'targeting fighters'
            for ship in selected:  # target small vessels
                ship.selector_emitter.template.position = ship.getPosition()
                ship.selector_emitter.template.size = (ship.size*30, ship.size*30, ship.size*30)
                ship.selector_emitter.emit(1, ship.impacto)
                ship.target = None
                ship.targetMode[0] = 'custom'
                ship.targetMode[1] = 1
        if symbol == key.W:
            print 'targeting destroyers'
            for ship in selected:  # target medium sized vessels
                ship.target = None
                ship.targetMode[0] = 'custom'
                ship.targetMode[1] = 5
        if symbol == key.E:
            print 'targeting cruisers'
            for ship in selected:  # target large vessels
                ship.target = None
                ship.targetMode[0] = 'custom'
                ship.targetMode[1] = 50
    if symbol == key.UP:
        controls['fw'] = True
    if symbol == key.LEFT:
        controls['lf'] = True
    if symbol == key.DOWN:
        controls['bk'] = True
    if symbol == key.RIGHT:
        controls['rt'] = True
    if symbol == key.A:
        controls['strl'] = True
    if symbol == key.S:
        controls['strr'] = True
    if symbol == key.SPACE:
        controls['f1'] = True


@win.event
def on_key_release(symbol, modifiers):
    if symbol == key.UP:
        controls['fw'] = False
    if symbol == key.LEFT:
        controls['lf'] = False
    if symbol == key.DOWN:
        controls['bk'] = False
    if symbol == key.RIGHT:
        controls['rt'] = False
    if symbol == key.A:
        controls['strl'] = False
    if symbol == key.S:
        controls['strr'] = False
    if symbol == key.SPACE:
        controls['f1'] = True


class ThreadMoveBola(threading.Thread):

    def run(self):
        pyglet.clock.schedule_interval(moveBola, (1.0 / 30.0))
        #pyglet.clock.schedule_interval(shipSpawner2, 5)


class ThreadSystemUpdate(threading.Thread):

    def run(self):
        pyglet.clock.schedule_interval(default_system.update, (1.0 / 30.0))

win.set_visible(True)


#def New_Map():
    #global yrot, xrot, ytra, xtra, ztra, camera, ships, battle, inBattle
    #inBattle = True
    #ships = []
    #yrot = 0.0
    #xrot = 0.0
    #ytra = 1.0
    #xtra = 0.0
    #ztra = -500

    #camera = Camera((xrot, yrot, ztra), scale=5)
    #battle = Battle(strat)
    #battle.LoadShips()
    #battle.Battle1()
    #if dothreads:
        #ThreadMoveBola().start()
        #ThreadSystemUpdate().start()
    #else:
        #pyglet.clock.schedule_interval(moveBola, (1.0 / 30.0))
        #pyglet.clock.schedule_interval(default_system.update, (1.0 / 30.0))

strat = stratMap()


if __name__ == '__main__':
    pyglet.app.run()

