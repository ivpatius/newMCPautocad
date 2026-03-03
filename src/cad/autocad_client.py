import win32com.client
import pythoncom
import time
from array import array
from typing import Optional, Dict, List, Any, Tuple


class AutoCADClient:
    """Расширенный клиент AutoCAD с поддержкой полного извлечения данных через COM."""

    def __init__(self):
        self.app = None
        self.doc = None
        self.model_space = None
        self.paper_space = None

    def connect(self) -> bool:
        """Подключение к запущенному экземпляру AutoCAD."""
        prog_ids = [
            "AutoCAD.Application", "AutoCAD.Application.25", "AutoCAD.Application.24.1",
            "AutoCAD.Application.24", "AutoCAD.Application.23.1", "AutoCAD.Application.23",
            "AutoCAD.Application.22", "AutoCAD.Application.21", "AutoCAD.Application.20.1",
            "AutoCAD.Application.20",
        ]

        last_error = None
        for prog_id in prog_ids:
            try:
                print(f"[*] Trying to connect via '{prog_id}'...")
                self.app = win32com.client.GetActiveObject(prog_id)
                self.doc = self.app.ActiveDocument
                self.model_space = self.doc.ModelSpace
                self.paper_space = self.doc.PaperSpace
                print(f"[+] Successfully connected via '{prog_id}'.")
                return True
            except Exception as e:
                last_error = e
                continue

        print(f"Error connecting to AutoCAD: {last_error}")
        print("Tip: Make sure AutoCAD is open and a drawing is active.")
        return False

    def _to_variant(self, point: Tuple[float, ...]) -> win32com.client.VARIANT:
        """Конвертация точки в COM-совместимый массив double."""
        coords = list(point) if len(point) == 3 else list(point) + [0.0]
        return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(map(float, coords)))

    # ========== РИСОВАНИЕ ==========
    def add_line(self, start_point, end_point):
        if not self.model_space:
            return None
        try:
            return self.model_space.AddLine(self._to_variant(start_point), self._to_variant(end_point))
        except Exception as e:
            print(f"Error in add_line: {e}")
            raise

    def add_circle(self, center, radius):
        if not self.model_space:
            return None
        try:
            return self.model_space.AddCircle(self._to_variant(center), float(radius))
        except Exception as e:
            print(f"Error in add_circle: {e}")
            raise

    def add_point(self, point):
        if not self.model_space:
            return None
        try:
            return self.model_space.AddPoint(self._to_variant(point))
        except Exception as e:
            print(f"Error in add_point: {e}")
            raise

    def add_arc(self, center, radius, start_angle, end_angle):
        if not self.model_space:
            return None
        try:
            return self.model_space.AddArc(self._to_variant(center), float(radius), float(start_angle),
                                           float(end_angle))
        except Exception as e:
            print(f"Error in add_arc: {e}")
            raise

    def add_spline(self, points, start_angle=15.0, end_angle=15.0):
        if not self.model_space:
            return None
        try:
            import math
            flattened = []
            for pt in points:
                flattened.extend([float(pt[0]), float(pt[1]), float(pt[2] if len(pt) > 2 else 0.0)])

            s_rad = math.radians(float(start_angle))
            e_rad = math.radians(float(end_angle))
            s_vec = [math.cos(s_rad), math.sin(s_rad), 0.0]
            e_vec = [math.cos(e_rad), math.sin(e_rad), 0.0]

            pts_array = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(flattened))
            start_tan = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(s_vec))
            end_tan = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(e_vec))

            return self.model_space.AddSpline(pts_array, start_tan, end_tan)
        except Exception as e:
            print(f"Error in add_spline: {e}")
            raise

    # ========== СЛОИ ==========
    def create_layer(self, layer_name, color_index=7):
        try:
            if not self.doc:
                return None
            layer = self.doc.Layers.Add(layer_name)
            layer.Color = int(color_index)
            print(f"[+] Layer '{layer_name}' created/updated with color {color_index}.")
            return layer
        except Exception as e:
            print(f"Error creating layer: {e}")
            return None

    def rename_layer(self, old_name, new_name):
        try:
            if not self.doc:
                return False
            layer = self.doc.Layers.Item(old_name)
            layer.Name = new_name
            print(f"[+] Layer '{old_name}' renamed to '{new_name}'.")
            return True
        except Exception as e:
            print(f"Error renaming layer: {e}")
            return False

    def change_layer_color(self, layer_name, color_index):
        try:
            if not self.doc:
                return False
            layer = self.doc.Layers.Item(layer_name)
            layer.Color = int(color_index)
            print(f"[+] Layer '{layer_name}' color changed to {color_index}.")
            return True
        except Exception as e:
            print(f"Error changing layer color: {e}")
            return False

    def get_layers_info(self) -> List[Dict]:
        """Получение полной информации о слоях."""
        try:
            if not self.doc:
                return []
            layers_data = []
            for layer in self.doc.Layers:
                try:
                    layers_data.append({
                        "name": layer.Name,
                        "color": layer.Color,
                        "linetype": layer.Linetype,
                        "lineweight": layer.Lineweight,
                        "on": layer.LayerOn,
                        "frozen": layer.Freeze,
                        "locked": layer.Lock,
                        "plot": layer.Plot,
                        "description": getattr(layer, 'Description', '')
                    })
                except:
                    continue
            return layers_data
        except Exception as e:
            print(f"Error retrieving layers: {e}")
            return []

    def set_layer_status(self, layer_name, is_on):
        try:
            if not self.doc:
                return False
            layer = self.doc.Layers.Item(layer_name)
            layer.LayerOn = is_on
            return True
        except Exception as e:
            print(f"Error setting layer status: {e}")
            return False

    # ========== ИЗВЛЕЧЕНИЕ ДАННЫХ (МАКСИМАЛЬНОЕ) ==========

    def get_all_entities_detailed(self, include_xdata: bool = True, include_dict: bool = True) -> List[Dict]:
        """
        Возвращает ПОЛНУЮ информацию обо всех объектах ModelSpace.
        Включает: общие свойства, геометрию, XData, Extension Dictionary.
        """
        entities = []
        skipped = 0

        if not self.model_space:
            return entities

        for ent in self.model_space:
            try:
                entity_data = self._extract_entity_full(ent, include_xdata, include_dict)
                if entity_data:
                    entities.append(entity_data)
                else:
                    skipped += 1
            except Exception as e:
                skipped += 1
                continue

        if skipped > 0:
            print(f"   ⚠️ Пропущено объектов: {skipped}")

        return entities

    def _extract_entity_full(self, ent, include_xdata: bool, include_dict: bool) -> Optional[Dict]:
        """Полное извлечение данных одного объекта."""
        try:
            # Базовые данные
            data = {
                "handle": str(ent.Handle) if hasattr(ent, 'Handle') else "UNKNOWN",
                "object_name": str(ent.ObjectName) if hasattr(ent, 'ObjectName') else "Unknown",
                "layer": str(ent.Layer) if hasattr(ent, 'Layer') else "0",
                "color": int(ent.Color) if hasattr(ent, 'Color') else 7,
                "linetype": str(ent.Linetype) if hasattr(ent, 'Linetype') else "ByLayer",
                "bounding_box": None,
                "area": None,
                "length": None,
                "coordinates": {},
                "xdata": None,
                "extension_dict": None,
            }

            # Дополнительные общие свойства
            try:
                if hasattr(ent, 'Lineweight'):
                    data["lineweight"] = int(ent.Lineweight)
            except:
                pass

            try:
                if hasattr(ent, 'EntityTransparency'):
                    data["transparency"] = int(ent.EntityTransparency)
            except:
                pass

            try:
                if hasattr(ent, 'Visible'):
                    data["visible"] = bool(ent.Visible)
            except:
                pass

            # Bounding box
            try:
                data["bounding_box"] = self._get_bounding_box(ent)
            except:
                pass

            # Числовые свойства
            try:
                if hasattr(ent, 'Area'):
                    data["area"] = float(ent.Area)
            except:
                pass

            try:
                if hasattr(ent, 'Length'):
                    data["length"] = float(ent.Length)
            except:
                pass

            try:
                if hasattr(ent, 'Volume'):
                    data["volume"] = float(ent.Volume)
            except:
                pass

            # Координаты
            try:
                data["coordinates"] = self._extract_coordinates(ent)
            except:
                pass

            # Тип-специфичные свойства
            try:
                type_props = self._extract_type_properties(ent)
                data.update(type_props)
            except:
                pass

            # XData
            if include_xdata:
                try:
                    data["xdata"] = self._extract_xdata(ent)
                except:
                    data["xdata"] = None

            # Extension Dictionary
            if include_dict:
                try:
                    if hasattr(ent, 'HasExtensionDictionary') and ent.HasExtensionDictionary:
                        data["extension_dict"] = self._extract_extension_dict(ent)
                except:
                    data["extension_dict"] = None

            return data

        except Exception as e:
            # Если совсем не получилось — возвращаем минимум
            try:
                return {
                    "handle": str(getattr(ent, 'Handle', 'ERROR')),
                    "object_name": str(getattr(ent, 'ObjectName', 'ERROR')),
                    "error": str(e)
                }
            except:
                return None

    def _get_bounding_box(self, ent) -> Optional[Dict]:
        """Получение ограничивающего прямоугольника объекта."""
        try:
            if hasattr(ent, 'GetBoundingBox'):
                min_pt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [0, 0, 0])
                max_pt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [0, 0, 0])
                ent.GetBoundingBox(min_pt, max_pt)
                return {
                    "min": [float(min_pt[0]), float(min_pt[1]), float(min_pt[2])],
                    "max": [float(max_pt[0]), float(max_pt[1]), float(max_pt[2])]
                }
        except:
            pass
        return None

    def _extract_coordinates(self, ent) -> Dict:
        """Извлечение координат в зависимости от типа объекта."""
        coords = {}
        obj_name = getattr(ent, 'ObjectName', '')

        try:
            if obj_name == "AcDbLine":
                if hasattr(ent, 'StartPoint'):
                    coords["start"] = [float(ent.StartPoint[0]), float(ent.StartPoint[1]), float(ent.StartPoint[2])]
                if hasattr(ent, 'EndPoint'):
                    coords["end"] = [float(ent.EndPoint[0]), float(ent.EndPoint[1]), float(ent.EndPoint[2])]

            elif obj_name in ["AcDbCircle", "AcDbArc"]:
                if hasattr(ent, 'Center'):
                    coords["center"] = [float(ent.Center[0]), float(ent.Center[1]), float(ent.Center[2])]

            elif obj_name == "AcDbBlockReference":
                if hasattr(ent, 'InsertionPoint'):
                    coords["insertion"] = [float(ent.InsertionPoint[0]), float(ent.InsertionPoint[1]),
                                           float(ent.InsertionPoint[2])]

            elif obj_name == "AcDbText":
                if hasattr(ent, 'InsertionPoint'):
                    coords["position"] = [float(ent.InsertionPoint[0]), float(ent.InsertionPoint[1]),
                                          float(ent.InsertionPoint[2])]

            elif obj_name == "AcDbPolyline":
                if hasattr(ent, 'Coordinates'):
                    raw = list(ent.Coordinates)
                    coords["vertices"] = [[float(raw[i]), float(raw[i + 1]), float(raw[i + 2])] for i in
                                          range(0, len(raw), 3)]

        except:
            pass

        return coords

    def _extract_type_properties(self, ent) -> Dict:
        """Извлечение свойств, специфичных для типа объекта (БЕЗ СПАМА ОШИБОК)."""
        props = {}
        obj_name = getattr(ent, 'ObjectName', '')

        # === AcDbLine ===
        if obj_name == "AcDbLine":
            try:
                props["angle"] = float(ent.Angle)
            except:
                pass
            try:
                if hasattr(ent, 'Delta'):
                    props["delta"] = [float(ent.Delta[0]), float(ent.Delta[1]), float(ent.Delta[2])]
            except:
                pass

        # === AcDbCircle ===
        elif obj_name == "AcDbCircle":
            try:
                props["radius"] = float(ent.Radius)
            except:
                pass
            try:
                props["diameter"] = float(ent.Diameter)
            except:
                pass
            try:
                props["circumference"] = float(ent.Circumference)
            except:
                pass

        # === AcDbArc ===
        elif obj_name == "AcDbArc":
            try:
                props["radius"] = float(ent.Radius)
            except:
                pass
            try:
                props["start_angle"] = float(ent.StartAngle)
            except:
                pass
            try:
                props["end_angle"] = float(ent.EndAngle)
            except:
                pass
            try:
                props["total_angle"] = float(ent.TotalAngle)
            except:
                pass
            try:
                props["arc_length"] = float(ent.ArcLength)
            except:
                pass

        # === AcDbPolyline ===
        elif obj_name == "AcDbPolyline":
            try:
                props["closed"] = bool(ent.Closed)
            except:
                pass
            try:
                props["constant_width"] = float(ent.ConstantWidth)
            except:
                pass
            try:
                props["elevation"] = float(ent.Elevation)
            except:
                pass
            # NumberOfVertices через координаты
            try:
                if hasattr(ent, 'Coordinates'):
                    coords = list(ent.Coordinates)
                    props["num_vertices"] = len(coords) // 3
            except:
                pass

        # === AcDbSpline ===
        elif obj_name == "AcDbSpline":
            try:
                props["degree"] = int(ent.Degree)
            except:
                pass
            try:
                props["closed"] = bool(ent.Closed)
            except:
                pass
            try:
                props["periodic"] = bool(ent.Periodic)
            except:
                pass
            try:
                props["num_control_points"] = int(ent.NumberOfControlPoints)
            except:
                pass
            try:
                props["num_fit_points"] = int(ent.NumberOfFitPoints)
            except:
                pass

        # === AcDbText ===
        elif obj_name == "AcDbText":
            try:
                props["text_string"] = str(ent.TextString)
            except:
                pass
            try:
                props["height"] = float(ent.Height)
            except:
                pass
            try:
                props["oblique_angle"] = float(ent.ObliqueAngle)
            except:
                pass
            try:
                props["style_name"] = str(ent.StyleName)
            except:
                pass
            try:
                props["rotation"] = float(ent.Rotation)
            except:
                pass
            # WidthFactor — может быть недоступен
            try:
                if hasattr(ent, 'WidthFactor'):
                    props["width_factor"] = float(ent.WidthFactor)
            except:
                pass

        # === AcDbMText ===
        elif obj_name == "AcDbMText":
            try:
                props["text_string"] = str(ent.TextString)
            except:
                pass
            try:
                props["height"] = float(ent.Height)
            except:
                pass
            try:
                props["width"] = float(ent.Width)
            except:
                pass
            try:
                props["attachment_point"] = int(ent.AttachmentPoint)
            except:
                pass
            try:
                props["rotation"] = float(ent.Rotation)
            except:
                pass
            try:
                props["style_name"] = str(ent.StyleName)
            except:
                pass

        # === AcDbBlockReference ===
        elif obj_name == "AcDbBlockReference":
            try:
                props["block_name"] = str(ent.Name)
            except:
                pass
            try:
                props["effective_name"] = str(getattr(ent, 'EffectiveName', ent.Name))
            except:
                pass
            try:
                props["scale_factors"] = {
                    "x": float(ent.XScaleFactor),
                    "y": float(ent.YScaleFactor),
                    "z": float(ent.ZScaleFactor)
                }
            except:
                pass
            try:
                props["rotation"] = float(ent.Rotation)
            except:
                pass
            try:
                props["is_dynamic"] = bool(getattr(ent, 'IsDynamicBlock', False))
            except:
                pass
            # Атрибуты
            try:
                if hasattr(ent, 'GetAttributes'):
                    attrs = []
                    for attr in ent.GetAttributes():
                        try:
                            attrs.append({
                                "tag": str(attr.TagString),
                                "text": str(attr.TextString),
                            })
                        except:
                            continue
                    props["attributes"] = attrs
            except:
                pass

        # === AcDbHatch ===
        elif obj_name == "AcDbHatch":
            try:
                props["pattern_name"] = str(ent.PatternName)
            except:
                pass
            try:
                props["pattern_scale"] = float(ent.PatternScale)
            except:
                pass
            try:
                props["pattern_angle"] = float(ent.PatternAngle)
            except:
                pass
            try:
                props["num_loops"] = int(ent.NumLoops)
            except:
                pass
            try:
                props["area"] = float(ent.Area)
            except:
                pass
            # SolidFill — может быть недоступен
            try:
                if hasattr(ent, 'SolidFill'):
                    props["solid_fill"] = bool(ent.SolidFill)
            except:
                pass
            try:
                props["gradient"] = bool(getattr(ent, 'Gradient', False))
            except:
                pass

        # === AcDbDimension ===
        elif "AcDbDimension" in obj_name:
            try:
                props["dimension_type"] = int(ent.DimensionType)
            except:
                pass
            try:
                props["measurement"] = float(ent.Measurement)
            except:
                pass
            try:
                props["style_name"] = str(ent.StyleName)
            except:
                pass
            try:
                props["text_string"] = str(getattr(ent, 'TextString', getattr(ent, 'TextOverride', '')))
            except:
                pass
            try:
                props["linear_scale_factor"] = float(getattr(ent, 'LinearScaleFactor', 1.0))
            except:
                pass

        # === AcDbMLeader ===
        elif obj_name == "AcDbMLeader":
            try:
                props["text_string"] = str(ent.TextString)
            except:
                pass

        return props

    def _extract_xdata(self, ent) -> Optional[Dict]:
        """Извлечение XData (Extended Data) объекта."""
        xdata = {}
        try:
            if hasattr(ent, 'GetXData'):
                known_apps = ["ACAD", "AUTODESK", "ROBOT", "REVIT"]

                for app_name in known_apps:
                    try:
                        result = ent.GetXData(app_name)
                        if result and len(result) >= 2:
                            xdata[app_name] = {
                                "type_codes": list(result[0]) if hasattr(result[0], '__iter__') else [result[0]],
                                "values": list(result[1]) if hasattr(result[1], '__iter__') else [result[1]]
                            }
                    except:
                        continue
        except:
            pass
        return xdata if xdata else None

    def _extract_extension_dict(self, ent) -> Optional[Dict]:
        """Извлечение Extension Dictionary объекта."""
        result = {}
        try:
            if hasattr(ent, 'ExtensionDictionary'):
                xdict = ent.ExtensionDictionary
                for key in xdict:
                    try:
                        item = xdict.Item(key)
                        if hasattr(item, 'Name'):
                            result[key] = {"type": "dictionary", "name": item.Name}
                        elif hasattr(item, 'Value'):
                            result[key] = {"type": "value", "value": item.Value}
                        else:
                            result[key] = {"type": "unknown"}
                    except:
                        continue
        except:
            pass
        return result if result else None

    # ========== КОМАНДЫ ==========
    def trim(self):
        """Вызов команды TRIM."""
        self.send_command("_TRIM")

    def send_command(self, command: str) -> bool:
        """Отправка сырой команды в AutoCAD."""
        try:
            if self.doc:
                self.doc.SendCommand(f"{command} ")
                return True
        except Exception as e:
            print(f"Error sending command: {e}")
        return False

    # ========== УТИЛИТЫ ==========
    def get_drawing_bounds(self) -> Optional[Dict]:
        """Получение границ чертежа (LIMMIN/LIMMAX)."""
        try:
            if not self.doc:
                return None
            return {
                "limmin": list(self.doc.GetVariable("LIMMIN")),
                "limmax": list(self.doc.GetVariable("LIMMAX")),
                "extmin": list(self.doc.GetVariable("EXTMIN")),
                "extmax": list(self.doc.GetVariable("EXTMAX"))
            }
        except:
            return None