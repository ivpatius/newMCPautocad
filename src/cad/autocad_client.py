import win32com.client
import pythoncom
import time
import logging
from array import array
from typing import Optional, Dict, List, Any, Tuple
from .dataclasses import (
    EntityProperties, BoundingBox, Coordinates,
    LayerInfo, BlockReference, TextEntity,
    DimensionEntity, DrawingMetadata
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('autocad_client.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutoCADClient:
    """
    Расширенный клиент AutoCAD с поддержкой полного извлечения данных через COM.
    ✅ Полное извлечение геометрии, свойств и bounding box
    ✅ Комплексная обработка ошибок и логирование
    """

    def __init__(self):
        self.app = None
        self.doc = None
        self.model_space = None
        self.paper_space = None
        self._connected = False

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
                logger.info(f"Trying to connect via '{prog_id}'...")
                self.app = win32com.client.GetActiveObject(prog_id)
                self.doc = self.app.ActiveDocument
                self.model_space = self.doc.ModelSpace
                self.paper_space = self.doc.PaperSpace
                self._connected = True
                logger.info(f"Successfully connected via '{prog_id}'.")
                return True
            except Exception as e:
                last_error = e
                logger.debug(f"Failed to connect via '{prog_id}': {e}")
                continue

        logger.error(f"Error connecting to AutoCAD: {last_error}")
        logger.error("Tip: Make sure AutoCAD is open and a drawing is active.")
        return False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.doc is not None

    def _to_variant(self, point: Tuple[float, ...]) -> win32com.client.VARIANT:
        """Конвертация точки в COM-совместимый массив double."""
        coords = list(point) if len(point) == 3 else list(point) + [0.0]
        return win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8,
            tuple(map(float, coords))
        )

    # ========== РИСОВАНИЕ ==========

    def add_line(self, start_point: Tuple[float, ...], end_point: Tuple[float, ...]):
        if not self.model_space:
            logger.error("ModelSpace not available")
            return None
        try:
            line = self.model_space.AddLine(
                self._to_variant(start_point),
                self._to_variant(end_point)
            )
            logger.info(f"Line created: {start_point} -> {end_point}")
            return line
        except Exception as e:
            logger.error(f"Error in add_line: {e}", exc_info=True)
            raise

    def add_circle(self, center: Tuple[float, ...], radius: float):
        if not self.model_space:
            logger.error("ModelSpace not available")
            return None
        try:
            circle = self.model_space.AddCircle(self._to_variant(center), float(radius))
            logger.info(f"Circle created: center={center}, radius={radius}")
            return circle
        except Exception as e:
            logger.error(f"Error in add_circle: {e}", exc_info=True)
            raise

    def add_point(self, point: Tuple[float, ...]):
        if not self.model_space:
            logger.error("ModelSpace not available")
            return None
        try:
            pt = self.model_space.AddPoint(self._to_variant(point))
            logger.info(f"Point created: {point}")
            return pt
        except Exception as e:
            logger.error(f"Error in add_point: {e}", exc_info=True)
            raise

    def add_arc(self, center: Tuple[float, ...], radius: float,
                start_angle: float, end_angle: float):
        if not self.model_space:
            logger.error("ModelSpace not available")
            return None
        try:
            arc = self.model_space.AddArc(
                self._to_variant(center),
                float(radius),
                float(start_angle),
                float(end_angle)
            )
            logger.info(f"Arc created: center={center}, radius={radius}")
            return arc
        except Exception as e:
            logger.error(f"Error in add_arc: {e}", exc_info=True)
            raise

    def add_spline(self, points: List[Tuple[float, ...]],
                   start_angle: float = 15.0, end_angle: float = 15.0):
        if not self.model_space:
            logger.error("ModelSpace not available")
            return None
        try:
            import math
            flattened = []
            for pt in points:
                flattened.extend([
                    float(pt[0]),
                    float(pt[1]),
                    float(pt[2] if len(pt) > 2 else 0.0)
                ])
            s_rad = math.radians(float(start_angle))
            e_rad = math.radians(float(end_angle))
            s_vec = [math.cos(s_rad), math.sin(s_rad), 0.0]
            e_vec = [math.cos(e_rad), math.sin(e_rad), 0.0]

            pts_array = win32com.client.VARIANT(
                pythoncom.VT_ARRAY | pythoncom.VT_R8,
                tuple(flattened)
            )
            start_tan = win32com.client.VARIANT(
                pythoncom.VT_ARRAY | pythoncom.VT_R8,
                tuple(s_vec)
            )
            end_tan = win32com.client.VARIANT(
                pythoncom.VT_ARRAY | pythoncom.VT_R8,
                tuple(e_vec)
            )

            spline = self.model_space.AddSpline(pts_array, start_tan, end_tan)
            logger.info(f"Spline created with {len(points)} points")
            return spline
        except Exception as e:
            logger.error(f"Error in add_spline: {e}", exc_info=True)
            raise

    # ========== СЛОИ ==========

    def create_layer(self, layer_name: str, color_index: int = 7):
        try:
            if not self.doc:
                logger.error("Document not available")
                return None
            layer = self.doc.Layers.Add(layer_name)
            layer.Color = int(color_index)
            logger.info(f"Layer '{layer_name}' created/updated with color {color_index}.")
            return layer
        except Exception as e:
            logger.error(f"Error creating layer: {e}", exc_info=True)
            return None

    def rename_layer(self, old_name: str, new_name: str) -> bool:
        try:
            if not self.doc:
                logger.error("Document not available")
                return False
            layer = self.doc.Layers.Item(old_name)
            layer.Name = new_name
            logger.info(f"Layer '{old_name}' renamed to '{new_name}'.")
            return True
        except Exception as e:
            logger.error(f"Error renaming layer: {e}", exc_info=True)
            return False

    def change_layer_color(self, layer_name: str, color_index: int) -> bool:
        try:
            if not self.doc:
                logger.error("Document not available")
                return False
            layer = self.doc.Layers.Item(layer_name)
            layer.Color = int(color_index)
            logger.info(f"Layer '{layer_name}' color changed to {color_index}.")
            return True
        except Exception as e:
            logger.error(f"Error changing layer color: {e}", exc_info=True)
            return False

    def get_layers_info(self) -> List[LayerInfo]:
        """Получение полной информации о слоях с типизацией."""
        try:
            if not self.doc:
                logger.error("Document not available")
                return []

            layers_data = []
            for layer in self.doc.Layers:
                try:
                    layers_data.append(LayerInfo(
                        name=str(layer.Name),
                        color=int(layer.Color),
                        linetype=str(layer.Linetype),
                        lineweight=int(layer.Lineweight) if hasattr(layer, 'Lineweight') else 0,
                        is_on=bool(layer.LayerOn),
                        is_frozen=bool(layer.Freeze),
                        is_locked=bool(layer.Lock),
                        viewport_frozen=bool(layer.ViewportDefault) if hasattr(layer, 'ViewportDefault') else False,
                        plot=bool(layer.Plot) if hasattr(layer, 'Plot') else True,
                        description=str(getattr(layer, 'Description', ''))
                    ))
                except Exception as e:
                    logger.warning(f"Error processing layer: {e}")
                    continue
            return layers_data
        except Exception as e:
            logger.error(f"Error retrieving layers: {e}", exc_info=True)
            return []

    def set_layer_status(self, layer_name: str, is_on: bool) -> bool:
        try:
            if not self.doc:
                logger.error("Document not available")
                return False
            layer = self.doc.Layers.Item(layer_name)
            layer.LayerOn = is_on
            logger.info(f"Layer '{layer_name}' turned {'ON' if is_on else 'OFF'}.")
            return True
        except Exception as e:
            logger.error(f"Error setting layer status: {e}", exc_info=True)
            return False

    # ========== ИЗВЛЕЧЕНИЕ ДАННЫХ (МАКСИМАЛЬНОЕ) ==========

    def get_all_entities_detailed(self, include_xdata: bool = True,
                                  include_dict: bool = True) -> List[EntityProperties]:
        """
        Возвращает ПОЛНУЮ информацию обо всех объектах ModelSpace.
        ✅ Включает: общие свойства, геометрию, XData, Extension Dictionary
        ✅ Каждая сущность с полным bounding box
        """
        entities = []
        skipped = 0

        if not self.model_space:
            logger.error("ModelSpace not available")
            return entities

        logger.info("Starting full entity extraction...")

        for ent in self.model_space:
            try:
                entity_data = self._extract_entity_full(ent, include_xdata, include_dict)
                if entity_data:
                    entities.append(entity_data)
                else:
                    skipped += 1
            except Exception as e:
                logger.warning(f"Error extracting entity: {e}")
                skipped += 1
                continue

        if skipped > 0:
            logger.warning(f"Skipped {skipped} entities during extraction.")

        logger.info(f"Extracted {len(entities)} entities successfully.")
        return entities

    def _extract_entity_full(self, ent, include_xdata: bool,
                             include_dict: bool) -> Optional[EntityProperties]:
        """Полное извлечение данных одного объекта с типизацией."""
        try:
            # Базовые данные
            data = EntityProperties(
                handle=str(ent.Handle) if hasattr(ent, 'Handle') else "UNKNOWN",
                object_name=str(ent.ObjectName) if hasattr(ent, 'ObjectName') else "Unknown",
                layer=str(ent.Layer) if hasattr(ent, 'Layer') else "0",
                color=int(ent.Color) if hasattr(ent, 'Color') else 7,
                linetype=str(ent.Linetype) if hasattr(ent, 'Linetype') else "ByLayer"
            )

            # Дополнительные общие свойства
            try:
                if hasattr(ent, 'Lineweight'):
                    data.lineweight = int(ent.Lineweight)
            except Exception:
                pass

            try:
                if hasattr(ent, 'EntityTransparency'):
                    data.transparency = int(ent.EntityTransparency)
            except Exception:
                pass

            try:
                if hasattr(ent, 'Visible'):
                    data.visible = bool(ent.Visible)
            except Exception:
                pass

            # ✅ Bounding box (ОБЯЗАТЕЛЬНО ДЛЯ ВСЕХ)
            try:
                data.bounding_box = self._get_bounding_box(ent)
            except Exception as e:
                logger.debug(f"Could not get bounding box: {e}")

            # Числовые свойства
            try:
                if hasattr(ent, 'Area'):
                    data.area = float(ent.Area)
            except Exception:
                pass

            try:
                if hasattr(ent, 'Length'):
                    data.length = float(ent.Length)
            except Exception:
                pass

            try:
                if hasattr(ent, 'Volume'):
                    data.volume = float(ent.Volume)
            except Exception:
                pass

            # Координаты
            try:
                data.coordinates = self._extract_coordinates(ent)
            except Exception as e:
                logger.debug(f"Could not extract coordinates: {e}")

            # Тип-специфичные свойства
            try:
                data.type_properties = self._extract_type_properties(ent)
            except Exception as e:
                logger.debug(f"Could not extract type properties: {e}")

            # XData
            if include_xdata:
                try:
                    data.xdata = self._extract_xdata(ent)
                except Exception:
                    data.xdata = None

            # Extension Dictionary
            if include_dict:
                try:
                    if hasattr(ent, 'HasExtensionDictionary') and ent.HasExtensionDictionary:
                        data.extension_dict = self._extract_extension_dict(ent)
                except Exception:
                    data.extension_dict = None

            return data

        except Exception as e:
            logger.error(f"Error extracting entity data: {e}", exc_info=True)
            # Если совсем не получилось — возвращаем минимум
            try:
                return EntityProperties(
                    handle=str(getattr(ent, 'Handle', 'ERROR')),
                    object_name=str(getattr(ent, 'ObjectName', 'ERROR')),
                    layer="0",
                    color=7,
                    linetype="ByLayer",
                    error=str(e)
                )
            except Exception:
                return None

    def _get_bounding_box(self, ent) -> Optional[BoundingBox]:
        """Получение ограничивающего прямоугольника объекта."""
        try:
            if hasattr(ent, 'GetBoundingBox'):
                min_pt = win32com.client.VARIANT(
                    pythoncom.VT_ARRAY | pythoncom.VT_R8,
                    [0, 0, 0]
                )
                max_pt = win32com.client.VARIANT(
                    pythoncom.VT_ARRAY | pythoncom.VT_R8,
                    [0, 0, 0]
                )
                ent.GetBoundingBox(min_pt, max_pt)
                return BoundingBox(
                    min_x=float(min_pt[0]), min_y=float(min_pt[1]), min_z=float(min_pt[2]),
                    max_x=float(max_pt[0]), max_y=float(max_pt[1]), max_z=float(max_pt[2])
                )
        except Exception as e:
            logger.debug(f"GetBoundingBox failed: {e}")
        return None

    def _extract_coordinates(self, ent) -> Coordinates:
        """Извлечение координат в зависимости от типа объекта."""
        coords = Coordinates()
        obj_name = getattr(ent, 'ObjectName', '')

        try:
            if obj_name == "AcDbLine":
                if hasattr(ent, 'StartPoint'):
                    coords.start = [
                        float(ent.StartPoint[0]),
                        float(ent.StartPoint[1]),
                        float(ent.StartPoint[2])
                    ]
                if hasattr(ent, 'EndPoint'):
                    coords.end = [
                        float(ent.EndPoint[0]),
                        float(ent.EndPoint[1]),
                        float(ent.EndPoint[2])
                    ]
            elif obj_name in ["AcDbCircle", "AcDbArc"]:
                if hasattr(ent, 'Center'):
                    coords.center = [
                        float(ent.Center[0]),
                        float(ent.Center[1]),
                        float(ent.Center[2])
                    ]
            elif obj_name == "AcDbBlockReference":
                if hasattr(ent, 'InsertionPoint'):
                    coords.insertion = [
                        float(ent.InsertionPoint[0]),
                        float(ent.InsertionPoint[1]),
                        float(ent.InsertionPoint[2])
                    ]
            elif obj_name == "AcDbText":
                if hasattr(ent, 'InsertionPoint'):
                    coords.insertion = [
                        float(ent.InsertionPoint[0]),
                        float(ent.InsertionPoint[1]),
                        float(ent.InsertionPoint[2])
                    ]
            elif obj_name == "AcDbPolyline":
                if hasattr(ent, 'Coordinates'):
                    raw = list(ent.Coordinates)
                    coords.vertices = [
                        [float(raw[i]), float(raw[i + 1]), float(raw[i + 2] if i + 2 < len(raw) else 0)]
                        for i in range(0, len(raw), 3)
                    ]
            elif obj_name == "AcDbPoint":
                if hasattr(ent, 'Coordinates'):
                    coords.point = [
                        float(ent.Coordinates[0]),
                        float(ent.Coordinates[1]),
                        float(ent.Coordinates[2])
                    ]
        except Exception as e:
            logger.debug(f"Coordinate extraction error: {e}")

        return coords

    def _extract_type_properties(self, ent) -> Dict[str, Any]:
        """Извлечение свойств, специфичных для типа объекта."""
        props = {}
        obj_name = getattr(ent, 'ObjectName', '')

        try:
            # === AcDbLine ===
            if obj_name == "AcDbLine":
                try:
                    props["angle"] = float(ent.Angle)
                except Exception:
                    pass
                try:
                    if hasattr(ent, 'Delta'):
                        props["delta"] = [
                            float(ent.Delta[0]),
                            float(ent.Delta[1]),
                            float(ent.Delta[2])
                        ]
                except Exception:
                    pass

            # === AcDbCircle ===
            elif obj_name == "AcDbCircle":
                try:
                    props["radius"] = float(ent.Radius)
                except Exception:
                    pass
                try:
                    props["diameter"] = float(ent.Diameter)
                except Exception:
                    pass
                try:
                    props["circumference"] = float(ent.Circumference)
                except Exception:
                    pass

            # === AcDbArc ===
            elif obj_name == "AcDbArc":
                try:
                    props["radius"] = float(ent.Radius)
                except Exception:
                    pass
                try:
                    props["start_angle"] = float(ent.StartAngle)
                except Exception:
                    pass
                try:
                    props["end_angle"] = float(ent.EndAngle)
                except Exception:
                    pass
                try:
                    props["total_angle"] = float(ent.TotalAngle)
                except Exception:
                    pass
                try:
                    props["arc_length"] = float(ent.ArcLength)
                except Exception:
                    pass

            # === AcDbPolyline ===
            elif obj_name == "AcDbPolyline":
                try:
                    props["closed"] = bool(ent.Closed)
                except Exception:
                    pass
                try:
                    props["constant_width"] = float(ent.ConstantWidth)
                except Exception:
                    pass
                try:
                    props["elevation"] = float(ent.Elevation)
                except Exception:
                    pass
                try:
                    if hasattr(ent, 'Coordinates'):
                        coords_list = list(ent.Coordinates)
                        props["num_vertices"] = len(coords_list) // 3
                except Exception:
                    pass

            # === AcDbSpline ===
            elif obj_name == "AcDbSpline":
                try:
                    props["degree"] = int(ent.Degree)
                except Exception:
                    pass
                try:
                    props["closed"] = bool(ent.Closed)
                except Exception:
                    pass
                try:
                    props["periodic"] = bool(ent.Periodic)
                except Exception:
                    pass
                try:
                    props["num_control_points"] = int(ent.NumberOfControlPoints)
                except Exception:
                    pass
                try:
                    props["num_fit_points"] = int(ent.NumberOfFitPoints)
                except Exception:
                    pass

            # === AcDbText ===
            elif obj_name == "AcDbText":
                try:
                    props["text_string"] = str(ent.TextString)
                except Exception:
                    pass
                try:
                    props["height"] = float(ent.Height)
                except Exception:
                    pass
                try:
                    props["oblique_angle"] = float(ent.ObliqueAngle)
                except Exception:
                    pass
                try:
                    props["style_name"] = str(ent.StyleName)
                except Exception:
                    pass
                try:
                    props["rotation"] = float(ent.Rotation)
                except Exception:
                    pass

            # === AcDbMText ===
            elif obj_name == "AcDbMText":
                try:
                    props["text_string"] = str(ent.TextString)
                except Exception:
                    pass
                try:
                    props["height"] = float(ent.Height)
                except Exception:
                    pass
                try:
                    props["width"] = float(ent.Width)
                except Exception:
                    pass
                try:
                    props["attachment_point"] = int(ent.AttachmentPoint)
                except Exception:
                    pass

            # === AcDbBlockReference ===
            elif obj_name == "AcDbBlockReference":
                try:
                    props["block_name"] = str(ent.Name)
                except Exception:
                    pass
                try:
                    props["effective_name"] = str(
                        getattr(ent, 'EffectiveName', ent.Name)
                    )
                except Exception:
                    pass
                try:
                    props["scale_factors"] = {
                        "x": float(ent.XScaleFactor),
                        "y": float(ent.YScaleFactor),
                        "z": float(ent.ZScaleFactor)
                    }
                except Exception:
                    pass
                try:
                    props["rotation"] = float(ent.Rotation)
                except Exception:
                    pass
                try:
                    props["is_dynamic"] = bool(
                        getattr(ent, 'IsDynamicBlock', False)
                    )
                except Exception:
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
                            except Exception:
                                continue
                        props["attributes"] = attrs
                except Exception:
                    pass

            # === AcDbHatch ===
            elif obj_name == "AcDbHatch":
                try:
                    props["pattern_name"] = str(ent.PatternName)
                except Exception:
                    pass
                try:
                    props["pattern_scale"] = float(ent.PatternScale)
                except Exception:
                    pass
                try:
                    props["pattern_angle"] = float(ent.PatternAngle)
                except Exception:
                    pass
                try:
                    props["num_loops"] = int(ent.NumLoops)
                except Exception:
                    pass

            # === AcDbDimension ===
            elif "AcDbDimension" in obj_name:
                try:
                    props["dimension_type"] = int(ent.DimensionType)
                except Exception:
                    pass
                try:
                    props["measurement"] = float(ent.Measurement)
                except Exception:
                    pass
                try:
                    props["style_name"] = str(ent.StyleName)
                except Exception:
                    pass
                try:
                    props["text_string"] = str(
                        getattr(ent, 'TextString', getattr(ent, 'TextOverride', ''))
                    )
                except Exception:
                    pass

            # === AcDbMLeader ===
            elif obj_name == "AcDbMLeader":
                try:
                    props["text_string"] = str(ent.TextString)
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"Type properties extraction error: {e}")

        return props

    def _extract_xdata(self, ent) -> Optional[Dict[str, Any]]:
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
                    except Exception:
                        continue
        except Exception:
            pass
        return xdata if xdata else None

    def _extract_extension_dict(self, ent) -> Optional[Dict[str, Any]]:
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
                    except Exception:
                        continue
        except Exception:
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
                logger.info(f"Command sent: {command}")
                return True
        except Exception as e:
            logger.error(f"Error sending command: {e}", exc_info=True)
        return False

    # ========== УТИЛИТЫ ==========

    def get_drawing_bounds(self) -> Optional[Dict[str, Any]]:
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
        except Exception as e:
            logger.error(f"Error getting drawing bounds: {e}", exc_info=True)
            return None

    def get_drawing_metadata(self) -> DrawingMetadata:
        """Получение метаданных чертежа."""
        try:
            if not self.doc:
                return DrawingMetadata()

            metadata = DrawingMetadata(
                drawing_name=str(self.doc.Name) if hasattr(self.doc, 'Name') else None,
                drawing_path=str(self.doc.FullName) if hasattr(self.doc, 'FullName') else None,
                acad_version=str(self.app.Version) if self.app else None
            )

            try:
                metadata.created_by = str(self.doc.SummaryInfo.Author)
            except Exception:
                pass

            return metadata
        except Exception as e:
            logger.error(f"Error getting metadata: {e}", exc_info=True)
            return DrawingMetadata()