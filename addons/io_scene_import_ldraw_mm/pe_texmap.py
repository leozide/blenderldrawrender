import mathutils


class PETexInfo:
    def __init__(self, image=None, matrix=None, v1=None, v2=None):
        self.image = image
        self.matrix = matrix
        self.v1 = v1
        self.v2 = v2


class PETexmap:
    def __init__(self):
        self.texture = None
        self.uvs = []

    def uv_unwrap_face(self, bm, face):
        uv_layer = bm.loops.layers.uv.verify()
        for i, loop in enumerate(face.loops):
            loop[uv_layer].uv = self.uvs[i]

    @staticmethod
    def build_pe_texmap(ldraw_node, child_node):
        pe_texmap = None

        if ldraw_node.pe_tex_info is not None:
            clean_line = child_node.line
            _params = clean_line.split()

            vert_count = len(child_node.vertices)

            # if we have uv data and a pe_tex_info, otherwise pass
            # # custom minifig head > 3626tex.dat (has no pe_tex) > 3626texpole.dat (has no uv data)
            if len(_params) > 14:  # use uvs provided in file
                pe_texmap = PETexmap()
                pe_texmap.texture = ldraw_node.pe_tex_info.image
                if vert_count == 3:
                    for i in range(vert_count):
                        x = round(float(_params[i * 2 + 11]), 3)
                        y = round(float(_params[i * 2 + 12]), 3)
                        uv = mathutils.Vector((x, y))
                        pe_texmap.uvs.append(uv)
                elif vert_count == 4:
                    for i in range(vert_count):
                        x = round(float(_params[i * 2 + 13]), 3)
                        y = round(float(_params[i * 2 + 14]), 3)
                        uv = mathutils.Vector((x, y))
                        pe_texmap.uvs.append(uv)
            else:  # calculate uvs
                if vert_count == 3:
                    # print("unwrap 3")
                    ...
                elif vert_count == 4:
                    # print("unwrap 4")
                    ...

        return pe_texmap
