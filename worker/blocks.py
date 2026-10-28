"""Bounded SVG instancing for repeated, translation-equivalent CAD blocks.

Geometry is rendered once per block/transform/resolved-property combination.
Attributes, clipped inserts and array inserts follow ezdxf's normal renderer.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from xml.etree import ElementTree as ET
from ezdxf import xclip
from ezdxf.addons.drawing import Frontend, layout, recorder, svg
from ezdxf.addons.drawing.properties import BackendProperties
from ezdxf.entities import Insert
from ezdxf.math import BoundingBox2d, Vec2

MAX_RECORDS = 1000000
MAX_INSTANCES = 50000


class Block:
    def __init__(self, identifier, records, position):
        self.identifier, self.records, self.position = identifier, records, position
        self.bounds = BoundingBox2d()
        for record in records:
            self.bounds.extend(record.bbox())


class BlockReference(recorder.DataRecord):
    def __init__(self, block, offset):
        super().__init__()
        self.block, self.offset = block, offset

    def bbox(self):
        if not self.block.bounds.has_data:
            return BoundingBox2d()
        return BoundingBox2d((self.block.bounds.extmin + self.offset,
                              self.block.bounds.extmax + self.offset))

    def transform_inplace(self, matrix):
        self.offset = Vec2(matrix.transform_direction(self.offset))


class InstancedSVGBackend(svg.SVGBackend):
    def __init__(self):
        super().__init__()
        self.blocks = {}
        self.record_count = self.instance_count = 0

    def store(self, record, properties):
        self.record_count += 1
        if self.record_count > MAX_RECORDS:
            raise ValueError('Drawing exceeds geometry limit')
        if isinstance(record, BlockReference):
            self.instance_count += 1
            if self.instance_count > MAX_INSTANCES:
                raise ValueError('Drawing exceeds block instance limit')
        super().store(record, properties)

    def get_xml_root_element(self, page, *, settings=layout.Settings(), render_box=None):
        # The app does not request margin cropping. The frontend applies CAD
        # clipping before recording; clipped branches never use instancing.
        if settings.crop_at_margins:
            raise ValueError('Instanced SVG does not support page margin cropping')
        bounds = render_box if render_box is not None else self.player().bbox()
        output_layout = layout.Layout(bounds, flip_y=True)
        page = output_layout.get_final_page(page, settings)
        if page.width == 0 or page.height == 0:
            return ET.Element('svg')
        matrix = output_layout.get_placement_matrix(page, settings=settings, top_origin=True)
        self.transformation_matrix = matrix
        renderer = self.make_backend(page, settings)
        renderer.configure(self.config)
        renderer.set_background(self.background)
        root_group = renderer.entities
        definitions = ET.SubElement(renderer.root, 'defs')

        def replay(records):
            regular = []
            def flush():
                if regular:
                    player = recorder.Player()
                    player.config, player.background = self.config, self.background
                    player.records, player.properties = regular, self.properties
                    player.replay(renderer)
                    regular.clear()
            for record in records:
                record.transform_inplace(matrix)
                if isinstance(record, BlockReference):
                    flush()
                    ET.SubElement(renderer.entities, 'use', {
                        'href': '#' + record.block.identifier,
                        'transform': f'translate({record.offset.x:.6f} {record.offset.y:.6f})',
                        'data-layer': self.properties[record.property_hash].layer[:255],
                    })
                else:
                    regular.append(record)
            flush()

        # All paths and definitions share one style table and one coordinate
        # transform. References retain their original position in paint order.
        for block in self.blocks.values():
            renderer.entities = ET.SubElement(definitions, 'g', {
                'id': block.identifier, 'stroke-linecap': 'round',
                'stroke-linejoin': 'round', 'fill-rule': 'evenodd',
            })
            replay(block.records)
        renderer.entities = root_group
        replay(self.records)
        return renderer.get_xml_root_element()


class InstancedFrontend(Frontend):
    def __init__(self, context, backend, **kwargs):
        super().__init__(context, backend, **kwargs)
        self.recorder = backend
        self.used_styles = set()
        self.active_blocks = set()
        self.unshared_depth = 0

    def draw_text_entity(self, entity, properties):
        self.used_styles.add(entity.dxf.get('style', 'Standard').casefold())
        return super().draw_text_entity(entity, properties)

    def draw_mtext_entity(self, entity, properties):
        self.used_styles.add(entity.dxf.get('style', 'Standard').casefold())
        return super().draw_mtext_entity(entity, properties)

    def draw_composite_entity(self, entity, properties):
        if not isinstance(entity, Insert):
            return super().draw_composite_entity(entity, properties)
        if len(self.active_blocks) >= 32:
            raise ValueError('Drawing exceeds block nesting limit')
        block = entity.block()
        unsafe = (self.unshared_depth or entity.attribs or entity.mcount > 1
                  or tuple(entity.dxf.extrusion) != (0.0, 0.0, 1.0)
                  or xclip.XClip(entity).has_clipping_path)
        if unsafe:
            self.unshared_depth += 1
            try:
                return super().draw_composite_entity(entity, properties)
            finally:
                self.unshared_depth -= 1
        if block is None or len(block) < 8:
            return super().draw_composite_entity(entity, properties)
        position = Vec2(entity.dxf.insert)
        attributes = tuple(sorted((k, str(v)) for k, v in entity.dxf.all_existing_dxf_attribs().items()
                                  if k not in ('handle', 'owner', 'insert')))
        # With a normal +Z extrusion and no clipping this is an XY projection:
        # insertion elevation does not change any output coordinate. Real CAD
        # files often have tiny elevation noise between identical floor plans.
        key = (attributes, properties.color, properties.pen,
               properties.layer, properties.lineweight, properties.linetype_name,
               tuple(properties.linetype_pattern), properties.linetype_scale,
               properties.units)
        if key in self.active_blocks:
            raise ValueError('Recursive block reference')
        cached = self.recorder.blocks.get(key)
        if cached is None:
            outer = self.recorder.records
            self.recorder.records = []
            self.active_blocks.add(key)
            try:
                super().draw_composite_entity(entity, properties)
                cached = Block('cad-block-' + str(len(self.recorder.blocks)),
                               self.recorder.records, position)
                self.recorder.blocks[key] = cached
            finally:
                self.active_blocks.remove(key)
                self.recorder.records = outer
        self.recorder.store(BlockReference(cached, position - cached.position),
                            BackendProperties(properties.color, properties.lineweight,
                                              properties.layer, properties.pen,
                                              entity.dxf.get('handle', '')))
