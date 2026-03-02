"""
Модуль ПОЛНОГО кэширования чертежа AutoCAD.
Собирает ВСЕ объекты, блоки, слои, стили, листы, системные переменные и пр.
Данные сохраняются в JSON и далее используются ТОЛЬКО из кэша.
"""
import json
import os
import pythoncom
from typing import Dict, List, Any, Optional
from datetime import datetime
from .autocad_client import AutoCADClient

CACHE_FILE = "drawing_cache.json"

class DrawingCache:
    """Полный кэш данных чертежа AutoCAD."""

    def __init__(self, acad_client: AutoCADClient):
        self.client = acad_client
        self.cache_data = {
            "metadata": {
                "drawing_name": None,
                "drawing_path": None,
                "last_update": None,
                "acad_version": None,
                "created_by": None
            },
            "system_variables": {},
            "layers": [],
            "linetypes": [],
            "text_styles": [],
            "dim_styles": [],
            "blocks": [],
            "block_references": [],
            "entities": [],
            "texts": [],
            "dimensions": [],
            "layouts": [],
            "dictionaries": {},
            "summary": {}
        }

    def full_cache_update(self):
        """Полное обновление ВСЕХ данных чертежа с защитой от сбоев COM."""
        print("🔄 Начинаем полное сканирование чертежа...")

        # Инициализация COM в этом потоке (обязательно!)
        pythoncom.CoInitialize()

        try:
            # Сбрасываем структуру кэша перед сбором
            self.cache_data = {
                "metadata": {"drawing_name": None, "drawing_path": None, "last_update": None, "acad_version": None, "created_by": None},
                "system_variables": {},
                "layers": [],
                "linetypes": [],
                "text_styles": [],
                "dim_styles": [],
                "blocks": [],
                "block_references": [],
                "entities": [],
                "texts": [],
                "dimensions": [],
                "layouts": [],
                "dictionaries": {},
                "summary": {}
            }

            doc = self.client.doc

            self._collect_metadata(doc)
            self._collect_system_variables(doc)
            self._collect_layers(doc)
            self._collect_linetypes(doc)
            self._collect_text_styles(doc)
            self._collect_dim_styles(doc)
            self._collect_blocks(doc)
            self._collect_block_references(doc)
            self._collect_entities(doc)
            self._collect_texts(doc)
            self._collect_dimensions(doc)
            self._collect_layouts(doc)       # защищённая версия
            self._collect_dictionaries(doc)  # защищённая версия

            self._generate_summary()
            self.cache_data["metadata"]["last_update"] = datetime.now().isoformat()

            self._save_cache()
            print(f"✅ Кэш обновлён: {len(self.cache_data['entities'])} объектов, "
                  f"{len(self.cache_data['block_references'])} блоков, "
                  f"{len(self.cache_data['texts'])} текстов, "
                  f"{len(self.cache_data['dimensions'])} размеров.")

        except Exception as e:
            print(f"❌ Ошибка при обновлении кэша: {e}")
            # Всё равно пытаемся сохранить то, что удалось собрать
            self.cache_data["metadata"]["last_update"] = datetime.now().isoformat()
            self._save_cache()
            print("⚠️ Кэш частично сохранён.")
        finally:
            pythoncom.CoUninitialize()

    def _save_cache(self):
        """Сохранение кэша в файл."""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"⚠️ Не удалось сохранить кэш: {e}")

    # ---------- СБОР МЕТАДАННЫХ ----------
    def _collect_metadata(self, doc):
        try:
            self.cache_data["metadata"]["drawing_name"] = doc.Name
            self.cache_data["metadata"]["drawing_path"] = doc.FullName
            self.cache_data["metadata"]["acad_version"] = doc.Application.Version
            try:
                self.cache_data["metadata"]["created_by"] = doc.SummaryInfo.Author
            except:
                pass
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора метаданных: {e}")

    # ---------- СИСТЕМНЫЕ ПЕРЕМЕННЫЕ ----------
    def _collect_system_variables(self, doc):
        important_vars = [
            "LIMMIN", "LIMMAX", "LASTPOINT", "TEXTSIZE", "TEXTSTYLE",
            "DIMSCALE", "DIMSTYLE", "CLAYER", "CECOLOR", "CELTYPE",
            "INSUNITS", "MEASUREMENT", "LUNITS", "LUPREC", "AUNITS",
            "AUPREC", "MENUECHO", "OSMODE", "SNAPMODE", "GRIDMODE",
            "ORTHOMODE", "POLARAD", "ATTREQ", "ATTDIA", "FILEDIA"
        ]
        for var in important_vars:
            try:
                self.cache_data["system_variables"][var] = doc.GetVariable(var)
            except:
                pass

    # ---------- СЛОИ ----------
    def _collect_layers(self, doc):
        layers = []
        try:
            for lyr in doc.Layers:
                try:
                    layers.append({
                        "name": lyr.Name,
                        "color": lyr.Color,
                        "linetype": lyr.Linetype,
                        "lineweight": lyr.Lineweight,
                        "on": lyr.LayerOn,
                        "frozen": lyr.Freeze,
                        "locked": lyr.Lock,
                        "viewport_frozen": lyr.ViewportDefault,
                        "plot": lyr.Plot,
                        "description": lyr.Description if hasattr(lyr, 'Description') else ""
                    })
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора слоёв: {e}")
        self.cache_data["layers"] = layers

    # ---------- ТИПЫ ЛИНИЙ ----------
    def _collect_linetypes(self, doc):
        ltypes = []
        try:
            for lt in doc.Linetypes:
                try:
                    ltypes.append({
                        "name": lt.Name,
                        "description": lt.Description,
                        "pattern": lt.Pattern if hasattr(lt, 'Pattern') else None
                    })
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора типов линий: {e}")
        self.cache_data["linetypes"] = ltypes

    # ---------- ТЕКСТОВЫЕ СТИЛИ ----------
    def _collect_text_styles(self, doc):
        styles = []
        try:
            for st in doc.TextStyles:
                try:
                    styles.append({
                        "name": st.Name,
                        "font_file": st.fontFile,
                        "big_font_file": st.BigFontFile,
                        "height": st.Height,
                        "width_factor": st.WidthFactor,
                        "oblique_angle": st.ObliqueAngle,
                        "generation_flag": st.TextGenerationFlag
                    })
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора текстовых стилей: {e}")
        self.cache_data["text_styles"] = styles

    # ---------- РАЗМЕРНЫЕ СТИЛИ ----------
    def _collect_dim_styles(self, doc):
        styles = []
        try:
            for ds in doc.DimStyles:
                try:
                    styles.append({"name": ds.Name})
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора размерных стилей: {e}")
        self.cache_data["dim_styles"] = styles

    # ---------- ОПРЕДЕЛЕНИЯ БЛОКОВ ----------
    def _collect_blocks(self, doc):
        blocks = []
        try:
            for blk in doc.Blocks:
                if blk.Name.startswith("*"):
                    continue
                try:
                    blocks.append({
                        "name": blk.Name,
                        "origin": [blk.Origin[0], blk.Origin[1], blk.Origin[2]],
                        "comment": blk.Comments if hasattr(blk, 'Comments') else "",
                        "explodable": blk.Explodable if hasattr(blk, 'Explodable') else True,
                        "has_attributes": False
                    })
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора определений блоков: {e}")
        self.cache_data["blocks"] = blocks

    # ---------- ВХОЖДЕНИЯ БЛОКОВ ----------
    def _collect_block_references(self, doc):
        refs = []
        try:
            model_space = doc.ModelSpace
            for ent in model_space:
                if ent.ObjectName == "AcDbBlockReference":
                    try:
                        ref = self._extract_block_reference_data(ent)
                        if ref:
                            refs.append(ref)
                    except:
                        continue
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора вхождений блоков: {e}")
        self.cache_data["block_references"] = refs

    def _extract_block_reference_data(self, br):
        data = {
            "handle": br.Handle,
            "name": br.Name,
            "effective_name": br.EffectiveName if hasattr(br, 'EffectiveName') else br.Name,
            "layer": br.Layer,
            "insertion_point": [br.InsertionPoint[0], br.InsertionPoint[1], br.InsertionPoint[2]],
            "scale": {
                "x": br.XScaleFactor,
                "y": br.YScaleFactor,
                "z": br.ZScaleFactor
            },
            "rotation": br.Rotation,
            "attributes": []
        }
        if hasattr(br, 'GetAttributes'):
            try:
                attrs = br.GetAttributes()
                for attr in attrs:
                    data["attributes"].append({
                        "tag": attr.TagString,
                        "text": attr.TextString,
                        "field_length": attr.FieldLength,
                        "position": [attr.InsertionPoint[0], attr.InsertionPoint[1], attr.InsertionPoint[2]],
                        "layer": attr.Layer
                    })
            except:
                pass
        return data

    # ---------- ВСЕ ПРИМИТИВЫ (КРОМЕ БЛОКОВ, ТЕКСТА, РАЗМЕРОВ) ----------
    def _collect_entities(self, doc):
        ents = []
        try:
            model_space = doc.ModelSpace
            for ent in model_space:
                obj_name = ent.ObjectName
                if obj_name in ["AcDbBlockReference", "AcDbText", "AcDbMText"] or "AcDbDimension" in obj_name:
                    continue
                try:
                    ent_data = self._extract_common_properties(ent)
                    ent_data.update(self._extract_type_specific_properties(ent))
                    ents.append(ent_data)
                except:
                    continue
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора примитивов: {e}")
        self.cache_data["entities"] = ents

    # ---------- ТЕКСТ ----------
    def _collect_texts(self, doc):
        texts = []
        try:
            model_space = doc.ModelSpace
            for ent in model_space:
                if ent.ObjectName in ["AcDbText", "AcDbMText"]:
                    try:
                        texts.append(self._extract_text_data(ent))
                    except:
                        continue
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора текста: {e}")
        self.cache_data["texts"] = texts

    # ---------- РАЗМЕРЫ ----------
    def _collect_dimensions(self, doc):
        dims = []
        try:
            model_space = doc.ModelSpace
            for ent in model_space:
                if "AcDbDimension" in ent.ObjectName:
                    try:
                        dims.append(self._extract_dimension_data(ent))
                    except:
                        continue
        except Exception as e:
            print(f"   ⚠️ Ошибка сбора размеров: {e}")
        self.cache_data["dimensions"] = dims

    # ---------- ЛИСТЫ (LAYOUTS) - БЕЗОПАСНАЯ ВЕРСИЯ ----------
    def _collect_layouts(self, doc):
        layouts = []
        try:
            for lay in doc.Layouts:
                try:
                    layout_info = {
                        "name": lay.Name,
                        "taborder": lay.TabOrder,
                    }
                    if hasattr(lay, 'ConfigName'):
                        layout_info["plot_config_name"] = lay.ConfigName
                    # Не читаем сложные объекты Plot
                    layouts.append(layout_info)
                except Exception as e:
                    print(f"   ⚠️ Ошибка при обработке листа {lay.Name}: {e}")
                    continue
        except Exception as e:
            print(f"   ⚠️ Не удалось получить коллекцию Layouts: {e}")
        self.cache_data["layouts"] = layouts

    # ---------- СЛОВАРИ NOD - БЕЗОПАСНАЯ ВЕРСИЯ ----------
    def _collect_dictionaries(self, doc):
        try:
            nod = doc.Dictionaries
            self.cache_data["dictionaries"] = self._walk_dictionary(nod)
        except Exception as e:
            print(f"   ⚠️ Ошибка при сборе словарей: {e}")
            self.cache_data["dictionaries"] = {}

    def _walk_dictionary(self, dict_obj):
        result = {}
        try:
            for key in dict_obj:
                try:
                    item = dict_obj.Item(key)
                    if hasattr(item, 'Name'):
                        result[key] = {"type": "dictionary", "name": item.Name}
                    else:
                        result[key] = {"type": "unknown"}
                except:
                    pass
        except:
            pass
        return result

    # ---------- ОБЩИЕ СВОЙСТВА ----------
    def _extract_common_properties(self, ent) -> Dict:
        props = {
            "handle": ent.Handle,
            "object_name": ent.ObjectName,
            "layer": ent.Layer,
            "color": ent.Color,
            "linetype": ent.Linetype,
            "lineweight": ent.Lineweight if hasattr(ent, 'Lineweight') else None,
            "visible": ent.Visible if hasattr(ent, 'Visible') else True,
            "coordinates": self._extract_coordinates(ent)
        }
        if hasattr(ent, 'Hyperlinks') and ent.Hyperlinks.Count > 0:
            props['has_hyperlinks'] = True
        if hasattr(ent, 'EntityTransparency'):
            props['transparency'] = ent.EntityTransparency
        return props

    def _extract_coordinates(self, entity) -> Dict:
        try:
            if hasattr(entity, 'StartPoint') and hasattr(entity, 'EndPoint'):
                return {
                    "start": [entity.StartPoint[0], entity.StartPoint[1], entity.StartPoint[2]],
                    "end": [entity.EndPoint[0], entity.EndPoint[1], entity.EndPoint[2]]
                }
            elif hasattr(entity, 'Center'):
                return {
                    "center": [entity.Center[0], entity.Center[1], entity.Center[2]]
                }
            elif hasattr(entity, 'InsertionPoint'):
                return {
                    "insertion": [entity.InsertionPoint[0], entity.InsertionPoint[1], entity.InsertionPoint[2]]
                }
            elif hasattr(entity, 'Coordinates'):
                return {"coordinates": list(entity.Coordinates)}
        except:
            pass
        return {}

    def _extract_type_specific_properties(self, ent) -> Dict:
        props = {}
        obj_name = ent.ObjectName
        try:
            if obj_name == "AcDbLine":
                props.update({
                    "length": ent.Length,
                    "angle": ent.Angle,
                    "delta": [ent.Delta[0], ent.Delta[1], ent.Delta[2]]
                })
            elif obj_name == "AcDbCircle":
                props.update({
                    "radius": ent.Radius,
                    "diameter": ent.Diameter,
                    "area": ent.Area,
                    "circumference": ent.Circumference
                })
            elif obj_name == "AcDbArc":
                props.update({
                    "radius": ent.Radius,
                    "start_angle": ent.StartAngle,
                    "end_angle": ent.EndAngle,
                    "total_angle": ent.TotalAngle,
                    "area": ent.Area,
                    "length": ent.ArcLength
                })
            elif obj_name == "AcDbPolyline":
                props.update({
                    "closed": ent.Closed,
                    "area": ent.Area,
                    "length": ent.Length,
                    "num_vertices": ent.NumberOfVertices
                })
            elif obj_name == "AcDbSpline":
                props.update({
                    "degree": ent.Degree,
                    "closed": ent.Closed,
                    "periodic": ent.Periodic,
                    "num_control_points": ent.NumberOfControlPoints,
                    "num_fit_points": ent.NumberOfFitPoints
                })
            elif obj_name == "AcDbPoint":
                props.update({
                    "point": [ent.Coordinates[0], ent.Coordinates[1], ent.Coordinates[2]]
                })
        except:
            pass
        return props

    def _extract_text_data(self, text_ent) -> Dict:
        data = {
            "handle": text_ent.Handle,
            "text": text_ent.TextString if hasattr(text_ent, 'TextString') else text_ent.TextString,
            "layer": text_ent.Layer,
            "height": text_ent.Height if hasattr(text_ent, 'Height') else text_ent.TextHeight,
            "style": text_ent.StyleName,
            "position": [text_ent.InsertionPoint[0], text_ent.InsertionPoint[1], text_ent.InsertionPoint[2]],
            "alignment": text_ent.Alignment,
            "rotation": text_ent.Rotation if hasattr(text_ent, 'Rotation') else 0
        }
        if text_ent.ObjectName == "AcDbMText":
            data["width"] = text_ent.Width
            data["attachment_point"] = text_ent.AttachmentPoint
        return data

    def _extract_dimension_data(self, dim) -> Dict:
        data = {
            "handle": dim.Handle,
            "dim_type": dim.DimensionType,
            "measurement": dim.Measurement,
            "text": dim.TextString if hasattr(dim, 'TextString') else dim.TextOverride,
            "style": dim.StyleName,
            "scale_factor": dim.LinearScaleFactor if hasattr(dim, 'LinearScaleFactor') else 1,
            "position": [dim.TextPosition[0], dim.TextPosition[1], dim.TextPosition[2]],
            "rotation": dim.TextRotation if hasattr(dim, 'TextRotation') else 0
        }
        if dim.DimensionType in [3, 4]:
            data["center"] = [dim.Center[0], dim.Center[1], dim.Center[2]]
            data["radius"] = dim.Measurement if dim.DimensionType == 4 else dim.Measurement / 2
        return data

    def _generate_summary(self):
        summary = {
            "total_entities": len(self.cache_data["entities"]),
            "total_blocks": len(self.cache_data["block_references"]),
            "total_texts": len(self.cache_data["texts"]),
            "total_dimensions": len(self.cache_data["dimensions"]),
            "layers_count": len(self.cache_data["layers"]),
            "linetypes_count": len(self.cache_data["linetypes"]),
            "text_styles_count": len(self.cache_data["text_styles"]),
            "dim_styles_count": len(self.cache_data["dim_styles"]),
            "block_definitions_count": len(self.cache_data["blocks"]),
            "layouts_count": len(self.cache_data["layouts"]),
            "by_type": {},
            "by_layer": {}
        }
        for ent in self.cache_data["entities"]:
            typ = ent["object_name"]
            layer = ent["layer"]
            summary["by_type"][typ] = summary["by_type"].get(typ, 0) + 1
            summary["by_layer"][layer] = summary["by_layer"].get(layer, 0) + 1
        self.cache_data["summary"] = summary

    # ---------- ЗАГРУЗКА КЭША ----------
    @staticmethod
    def load_cache() -> Optional[Dict]:
        """
        Загружает кэш из файла.
        Возвращает None, если:
        - файл не существует,
        - файл повреждён,
        - структура кэша устарела (нет ключа 'metadata').
        """
        if not os.path.exists(CACHE_FILE):
            return None
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'metadata' not in data or 'last_update' not in data.get('metadata', {}):
                print("[DrawingCache] Обнаружен устаревший формат кэша. Требуется пересоздание.")
                return None
            return data
        except Exception as e:
            print(f"[DrawingCache] Ошибка загрузки кэша: {e}")
            return None