import sc2
import random
from sc2.constants import LARVA, ZERGLING, QUEEN, OVERLORD, DRONE, HYDRALISK, HYDRALISKDEN
from sc2.constants import HATCHERY, SPAWNINGPOOL, EXTRACTOR, LAIR
from sc2.constants import RESEARCH_ZERGLINGMETABOLICBOOST, EFFECT_INJECTLARVA, AbilityId

class ZergInfestationStrategyBot(sc2.BotAI):
    def __init__(self):
        """Inicializa variables de control de flujo

        extractors: Contador de gaysers de vespeno para tener 1 por hatchery
        spawning_pool_started: Flag que permite validar que ya se creo un spawning pool
        queen_counter: Contador de Queens para tener 1 por hatchery
        mboost_started: Flag que permite validar el desarrollo de habilidad metabolic_bost para Zerglings

        """
        self.extractors = 0
        self.spawning_pool_started = False
        self.queen_counter = 0
        self.mboost_started = False


    async def on_step(self, iteration):
        """Ciclo infinito del juego"""

        self.hq = self.townhalls.random # Elegir un ayuntamiento ( Hatchery, Lair, Hive ) aleatorio en cada paso.
        self.larvae = self.units(LARVA) # Lista de larvas disponibles

        await self.build_and_distribute_workers()
        await self.explore_the_map()
        await self.launch_attack_if_we_are_ready()
        await self.research_zergling_metabolic_boost_when_possible()
        await self.build_supply_when_necessary()
        await self.try_to_build_hydralisks_quickly()
        await self.try_to_build_zerglings_quickly()
        await self.build_an_expansion()
        await self.build_queens_continously()


    async def build_and_distribute_workers(self):
        """Construir la cantidad de obreros ideal y distributir trabajadores automaticamente"""

        await self.distribute_workers()
        if self.hq.assigned_harvesters < self.hq.ideal_harvesters:
            if self.can_afford(DRONE) and self.larvae.amount > 0:
                await self.do(self.larvae.random.train(DRONE))

        if self.extractors == 0:
            drone = self.workers.random
            target = self.state.vespene_geyser.closest_to(drone.position)
            err = await self.do(drone.build(EXTRACTOR, target))
            if not err:
                self.extractors += 1

        if self.extractors < self.units(HATCHERY).amount and self.units(LAIR).ready.exists:
            if self.can_afford(EXTRACTOR) and self.workers.exists:
                drone = self.workers.random
                target = self.state.vespene_geyser.closest_to(drone.position)
                err = await self.do(drone.build(EXTRACTOR, target))
                if not err:
                    self.extractors += 1


    async def explore_the_map(self):
        """Mantener Overlords explorando el mapa continuamente de base en base"""

        scout_locations = [location for location in self.expansion_locations if
                           location not in self.enemy_start_locations]

        for overlord in self.units(OVERLORD).idle:
            await self.do(overlord.move(random.choice(scout_locations)))

    async def launch_attack_if_we_are_ready(self):
        """Esperar para lanzar un ataque cuando se cuenten con las unidades necesarias

        Usar 2 estrategias distintas de ataques:
        - Enviar todas las unidades en espera cuando ya se cuente con 10 Hidraliscos.
        - Enviar 50 Zerglins disponibles.

        Cada ataque se envia hacia alguna estructura enemiga conocida aleatoria
        o en su defecto a la posicion inicial del enemigo.
        """

        forces = self.units(ZERGLING) | self.units(HYDRALISK)
        target = self.known_enemy_structures.random_or(self.enemy_start_locations[0]).position

        if self.units(HYDRALISK).amount > 10:
            for unit in forces.idle:
                await self.do(unit.attack(target))

        if self.units(ZERGLING).amount > 50:
            for unit in forces.idle:
                await self.do(unit.attack(target))

    async def research_zergling_metabolic_boost_when_possible(self):
        """Investigar y mejorar Zerglings con Metabolic Boost cuando sea posible"""

        if self.vespene >= 100:
            sp = self.units(SPAWNINGPOOL).ready
            if sp.exists and self.minerals >= 100 and not self.mboost_started:
                await self.do(sp.first(RESEARCH_ZERGLINGMETABOLICBOOST))
                self.mboost_started = True

    async def build_supply_when_necessary(self):
        """Construir Overlords cuando sea necesario"""

        if self.supply_left < 2:
            if self.can_afford(OVERLORD) and self.larvae.exists:
                await self.do(self.larvae.random.train(OVERLORD))

    async def try_to_build_zerglings_quickly(self):
        """Tratar de construir un SpawningPool lo mas rapido posible para producir Zerglings"""

        if not self.spawning_pool_started:
            if self.can_afford(SPAWNINGPOOL) and self.workers.exists:
                for d in range(4, 15):
                    pos = self.hq.position.to2.towards(self.game_info.map_center, d)
                    if await self.can_place(SPAWNINGPOOL, pos):
                        drone = self.workers.closest_to(pos)
                        err = await self.do(drone.build(SPAWNINGPOOL, pos))
                        if not err:
                            self.spawning_pool_started = True
                            break

        if self.units(SPAWNINGPOOL).ready.exists:
            if self.larvae.exists and self.can_afford(ZERGLING):
                await self.do(self.larvae.random.train(ZERGLING))


    async def try_to_build_hydralisks_quickly(self):
        """Evolucionar Hatchery, construir un Hydralisken para producir Hidraliscos rapidamente"""

        if self.units(SPAWNINGPOOL).ready.exists:
            if not (self.units(LAIR).amount > 0):
                if self.can_afford(LAIR):
                    await self.do(self.townhalls.first.build(LAIR))

        if self.units(LAIR).ready.exists:
            if not (self.units(HYDRALISKDEN).exists or self.already_pending(HYDRALISKDEN)):
                if self.can_afford(HYDRALISKDEN):
                    await self.build(HYDRALISKDEN, near=self.townhalls.first)

        if self.units(HYDRALISKDEN).ready.exists:
            if self.can_afford(HYDRALISK) and self.larvae.exists:
                await self.do(self.larvae.random.train(HYDRALISK))

    async def build_an_expansion(self):
        """Construir expansiones en los lugares mas adecuados de forma aleatoria"""

        scout_locations = [location for location in self.expansion_locations if
                           location not in self.enemy_start_locations]
        if self.minerals > 400 and self.workers.exists:
            pos = random.choice(scout_locations)
            if await self.can_place(HATCHERY, pos):
                self.spawning_pool_started = True
                await self.do(self.workers.random.build(HATCHERY, pos))


    async def build_queens_continously(self):
        """Construir Queens para mantener un volumen frecuente de larvas """

        for queen in self.units(QUEEN).idle:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                await self.do(queen(EFFECT_INJECTLARVA, self.hq))

        if self.queen_counter < self.units(HATCHERY).amount and self.units(SPAWNINGPOOL).ready.exists:
            if self.can_afford(QUEEN):
                r = await self.do(self.hq.train(QUEEN))
                if not r:
                    self.queeen_started = True