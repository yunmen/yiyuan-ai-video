# -*- coding: utf-8 -*-
'''
@文件    :gen_code_service.py
@说明    :
@时间    :2025/08/28 16:37:01
@作者    :睿
@版本    :1.0
'''
import importlib
from tortoise import Model
from tortoise.fields import Field
from generate.utils.file_utils import create_code_file, delete_code_file
from generate.utils.jinja2_utils import Jinja2Utils
from generate.utils.field_utils import get_field_type, get_field_default
from generate.utils.split_utils import convert_model_to_path, split_and_lowercase


class GenCodeService:
    def __init__(self, model_name: str, output: bool = False, overwrite: bool = False, author: str = "浪晋"):
        self.model = model_name
        self.output = output
        self.overwrite = overwrite
        self.author = author
        self.path, self.modele = convert_model_to_path(model_name)
        self.file = split_and_lowercase(model_name)[-1]
        self.engine = Jinja2Utils()
        self.exclude_fields = ["id", "deleted", "create_time", "update_time"]
    
    def get_model_fields(self):
        module = importlib.import_module("app.models")
        model: Model = getattr(module, self.model)
        fields = []
        for field_name, field_obj in model._meta.fields_map.items():
            if field_name in self.exclude_fields:
                continue
            obj: Field = field_obj
            field_info = {
                "name": field_name,
                "type": get_field_type(obj),
                "default": get_field_default(obj),
                "description": obj.description
            }
            fields.append(field_info)
        return fields

    def generate_schema_code(self):
        schemas_path = f'app/schemas/{self.path}.py'
        fields = self.get_model_fields()
        content = self.engine.generate("schema.j2",
            file_name=self.file,
            author=self.author,
            fields=fields
        )
        if self.output:
            create_code_file(schemas_path, content, overwrite=self.overwrite)
        return content

    def generate_crud_code(self):
        schemas_path = f'app/cruds/{self.path}.py'
        fields = self.get_model_fields()
        content = self.engine.generate("crud.j2",
            module_name=self.modele,
            file_name=self.file,
            model_name=self.model,
            author=self.author,
            fields=fields
        )
        if self.output:
            create_code_file(schemas_path, content, overwrite=self.overwrite)
        return content


    def generate_service_code(self):
        schemas_path = f'app/services/{self.path}.py'
        fields = self.get_model_fields()
        content = self.engine.generate("service.j2",
            module_name=self.modele,
            file_name=self.file,
            model_name=self.model,
            author=self.author,
            fields=fields
        )
        if self.output:
            create_code_file(schemas_path, content, overwrite=self.overwrite)
        return content


    def generate_controller_code(self):
        schemas_path = f'app/controllers/{self.path}.py'
        fields = self.get_model_fields()
        content = self.engine.generate("controller.j2",
            module_name=self.modele,
            file_name=self.file,
            model_name=self.model,
            author=self.author,
            fields=fields
        )
        if self.output:
            create_code_file(schemas_path, content, overwrite=self.overwrite)
        return content

    def generate_route_code(self):
        schemas_path = f'app/routes/admin/{self.path}.py'
        fields = self.get_model_fields()
        content = self.engine.generate("route.j2",
            module_name=self.modele,
            file_name=self.file,
            model_name=self.model,
            author=self.author,
            fields=fields
        )
        if self.output:
            create_code_file(schemas_path, content, overwrite=self.overwrite)
        return content
    

    def generate_code(self):
        self.generate_schema_code()
        self.generate_crud_code()
        self.generate_service_code()
        # self.generate_controller_code()
        self.generate_route_code()