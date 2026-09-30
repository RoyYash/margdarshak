import unittest

from app import make_graph
from vehicle_simulation import (
    add_vehicle_alternate_roads,
    add_road_metadata,
    calculate_valid_route,
    connect_simulation_components,
    get_vehicle_constraints,
    is_road_allowed,
)


class VehicleSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nodes, edges = make_graph(27, seed=42, traffic="Rush Hour")
        cls.coordinates = {
            node["id"]: (node["x"] * 0.001, node["y"] * 0.001) for node in nodes
        }
        cls.roads = connect_simulation_components(
            add_road_metadata(edges),
            list(cls.coordinates),
            cls.coordinates,
            1.0,
        )

    def test_vehicle_profiles_define_distinct_road_classes(self):
        self.assertEqual(
            get_vehicle_constraints("2-Wheeler")["allowed_classes"],
            {"narrow", "medium", "arterial"},
        )
        self.assertEqual(
            get_vehicle_constraints("3-Wheeler")["allowed_classes"],
            {"medium", "arterial"},
        )
        self.assertEqual(
            get_vehicle_constraints("Heavy Vehicle")["allowed_classes"],
            {"arterial"},
        )

    def test_all_selectable_locations_have_permitted_routes(self):
        for vehicle_type in ("2-Wheeler", "3-Wheeler", "Heavy Vehicle"):
            for start in range(23):
                for destination in range(23):
                    if start == destination:
                        continue
                    route = calculate_valid_route(
                        start, destination, vehicle_type, self.roads
                    )
                    self.assertIsNotNone(route, (vehicle_type, start, destination))
                    for first, second in zip(route, route[1:]):
                        road = next(
                            road
                            for road in self.roads
                            if {road["a"], road["b"]} == {first, second}
                        )
                        self.assertTrue(is_road_allowed(road, vehicle_type))

    def test_heavy_vehicle_reroutes_around_closed_road(self):
        route = calculate_valid_route(0, 12, "Heavy Vehicle", self.roads)
        closed_edge = tuple(sorted((route[0], route[1])))
        roads = [dict(road) for road in self.roads]
        for road in roads:
            if tuple(sorted((road["a"], road["b"]))) == closed_edge:
                road["closed"] = True
        alternate = calculate_valid_route(
            0, 12, "Heavy Vehicle", roads, {closed_edge}
        )
        if alternate is None:
            roads.extend(
                add_vehicle_alternate_roads(
                    roads,
                    list(self.coordinates),
                    self.coordinates,
                    "Heavy Vehicle",
                )
            )
            alternate = calculate_valid_route(
                0, 12, "Heavy Vehicle", roads, {closed_edge}
            )
        self.assertIsNotNone(alternate)
        self.assertNotEqual(tuple(sorted(alternate[:2])), closed_edge)
        for first, second in zip(alternate, alternate[1:]):
            road = next(
                road
                for road in roads
                if {road["a"], road["b"]} == {first, second}
            )
            self.assertTrue(is_road_allowed(road, "Heavy Vehicle", {closed_edge}))

    def test_heavy_vehicle_never_uses_non_supporting_or_restricted_roads(self):
        for road in self.roads:
            if road["road_class"] != "arterial" or road["restricted"]:
                self.assertFalse(is_road_allowed(road, "Heavy Vehicle"))


if __name__ == "__main__":
    unittest.main()
