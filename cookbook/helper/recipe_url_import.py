import random
import re
from json import JSONDecodeError
from isodate import parse_duration as iso_parse_duration
from isodate.isoerror import ISO8601Error

import microdata
from bs4 import BeautifulSoup
from cookbook.helper.ingredient_parser import parse as parse_single_ingredient
from cookbook.models import Keyword
from django.utils.dateparse import parse_duration
from django.utils.translation import gettext as _
from recipe_scrapers._utils import get_minutes, normalize_string


def get_from_html_old(html_text, url, space):
    soup = BeautifulSoup(html_text, "html.parser")

    # first try finding ld+json as its most common
    for ld in soup.find_all('script', type='application/ld+json'):
        try:
            ld_json = json.loads(ld.string.replace('\n', ''))
            if type(ld_json) != list:
                ld_json = [ld_json]

            for ld_json_item in ld_json:
                # recipes type might be wrapped in @graph type
                if '@graph' in ld_json_item:
                    for x in ld_json_item['@graph']:
                        if '@type' in x and x['@type'] == 'Recipe':
                            ld_json_item = x

                if ('@type' in ld_json_item and ld_json_item['@type'] == 'Recipe'):
                    return JsonResponse(find_recipe_json(ld_json_item, url, space))
        except JSONDecodeError:
            return JsonResponse(
                {
                    'error': True,
                    'msg': _('The requested site provided malformed data and cannot be read.')  # noqa: E501
                },
                status=400)

    # now try to find microdata
    items = microdata.get_items(html_text)
    for i in items:
        md_json = json.loads(i.json())
        if 'schema.org/Recipe' in str(md_json['type']):
            return JsonResponse(find_recipe_json(md_json['properties'], url))

    return JsonResponse(
        {
            'error': True,
            'msg': _('The requested site does not provide any recognized data format to import the recipe from.')  # noqa: E501
        },
        status=400)


def find_recipe_json(ld_json, url, space):
    ld_json['name'] = parse_name(ld_json['name'])

    except AttributeError:
        description = ''

    if 'recipeIngredient' in ld_json:
        ld_json['recipeIngredient'] = parse_ingredients(ld_json['recipeIngredient'])
    else:
        ld_json['recipeIngredient'] = ""

    try:
        servings = scrape.yields()
        servings = int(re.findall(r'\b\d+\b', servings)[0])
    except (AttributeError, ValueError, IndexError):
        servings = 1
    recipe_json['servings'] = servings

    try:
        recipe_json['prepTime'] = get_minutes(scrape.schema.data.get("prepTime")) or 0
    except AttributeError:
        recipe_json['prepTime'] = 0
    try:
        recipe_json['cookTime'] = get_minutes(scrape.schema.data.get("cookTime")) or 0
    except AttributeError:
        recipe_json['cookTime'] = 0
    if recipe_json['cookTime'] + recipe_json['prepTime'] == 0:
        try:
            recipe_json['prepTime'] = get_minutes(scrape.total_time()) or 0
        except AttributeError:
            pass
    keywords = []
    if 'keywords' in ld_json:
        keywords += listify_keywords(ld_json['keywords'])
    if 'recipeCategory' in ld_json:
        keywords += listify_keywords(ld_json['recipeCategory'])
    if 'recipeCuisine' in ld_json:
        keywords += listify_keywords(ld_json['recipeCuisine'])
    try:
        ld_json['keywords'] = parse_keywords(list(set(map(str.casefold, keywords))), space)
    except TypeError:
        pass

    if 'recipeInstructions' in ld_json:
        ld_json['recipeInstructions'] = parse_instructions(ld_json['recipeInstructions'])
    else:
        ld_json['recipeInstructions'] = ""

    if 'image' in ld_json:
        ld_json['image'] = parse_image(ld_json['image'])
    else:
        ld_json['image'] = ""

    if 'description' in ld_json:
        ld_json['description'] = normalize_string(ld_json['description'])
    else:
        ld_json['description'] = ""

    if 'cookTime' in ld_json:
        ld_json['cookTime'] = parse_cooktime(ld_json['cookTime'])
    else:
        ld_json['cookTime'] = 0

    if 'prepTime' in ld_json:
        ld_json['prepTime'] = parse_cooktime(ld_json['prepTime'])
    else:
        ld_json['prepTime'] = 0

    if 'servings' in ld_json:
        ld_json['servings'] = parse_servings(ld_json['servings'])
    elif 'recipeYield' in ld_json:
        ld_json['servings'] = parse_servings(ld_json['recipeYield'])
    else:
        ld_json['servings'] = 1

    for key in list(ld_json):
        if key not in [
            'prepTime', 'cookTime', 'image', 'recipeInstructions',
            'keywords', 'name', 'recipeIngredient', 'servings', 'description'
        ]:
            ld_json.pop(key, None)

    return ld_json


def get_from_scraper(scrape, space):
    # converting the scrape_me object to the existing json format based on ld+json

    recipe_json = {}
    recipe_json['name'] = scrape.title()

    try:
        description = scrape.schema.data.get("description") or ''
        recipe_json['prepTime'] = get_minutes(scrape.schema.data.get("prepTime")) or 0
        recipe_json['cookTime'] = get_minutes(scrape.schema.data.get("cookTime")) or 0
    except AttributeError:
        description = ''
        recipe_json['prepTime'] = 0
        recipe_json['cookTime'] = 0

    recipe_json['description'] = normalize_string(description)

    try:
        servings = scrape.yields()
        servings = int(re.findall(r'\b\d+\b', servings)[0])
    except (AttributeError, ValueError, IndexError):
        servings = 1
    recipe_json['servings'] = servings

    if recipe_json['cookTime'] + recipe_json['prepTime'] == 0:
        try:
            recipe_json['prepTime'] = scrape.total_time()
        except AttributeError:
            pass

    try:
        recipe_json['image'] = scrape.image()
    except AttributeError:
        pass

    keywords = []
    try:
        if scrape.schema.data.get("keywords"):
            keywords += listify_keywords(scrape.schema.data.get("keywords"))
        if scrape.schema.data.get('recipeCategory'):
            keywords += listify_keywords(scrape.schema.data.get("recipeCategory"))
        if scrape.schema.data.get('recipeCuisine'):
            keywords += listify_keywords(scrape.schema.data.get("recipeCuisine"))
        recipe_json['keywords'] = parse_keywords(list(set(map(str.casefold, keywords))), space)
    except AttributeError:
        recipe_json['keywords'] = keywords

    try:
        ingredients = []
        for x in scrape.ingredients():
            try:
                amount, unit, ingredient, note = parse_single_ingredient(x)
                if ingredient:
                    ingredients.append(
                        {
                            'amount': amount,
                            'unit': {
                                'text': unit,
                                'id': random.randrange(10000, 99999)
                            },
                            'ingredient': {
                                'text': ingredient,
                                'id': random.randrange(10000, 99999)
                            },
                            'note': note,
                            'original': x
                        }
                    )
            except Exception:
                ingredients.append(
                    {
                        'amount': 0,
                        'unit': {
                            'text': '',
                            'id': random.randrange(10000, 99999)
                        },
                        'ingredient': {
                            'text': x,
                            'id': random.randrange(10000, 99999)
                        },
                        'note': '',
                        'original': x
                    }
                )
        recipe_json['recipeIngredient'] = ingredients
    except AttributeError:
        recipe_json['recipeIngredient'] = ingredients

    try:
        recipe_json['recipeInstructions'] = scrape.instructions()
    except AttributeError:
        recipe_json['recipeInstructions'] = ""

    recipe_json['recipeInstructions'] += "\n\nImported from " + scrape.url
    return recipe_json


def parse_name(name):
    if type(name) == list:
        try:
            name = name[0]
        except Exception:
            name = 'ERROR'
    return normalize_string(name)


def parse_ingredients(ingredients):
    # some pages have comma separated ingredients in a single array entry
    try:
        if type(ingredients[0]) == dict:
            return ingredients
    except (KeyError, IndexError):
        pass

    if (len(ingredients) == 1 and type(ingredients) == list):
        ingredients = ingredients[0].split(',')
    elif type(ingredients) == str:
        ingredients = ingredients.split(',')

    for x in ingredients:
        if '\n' in x:
            ingredients.remove(x)
            for i in x.split('\n'):
                ingredients.insert(0, i)

    ingredient_list = []

    for x in ingredients:
        if x.replace(' ', '') != '':
            x = x.replace('&frac12;', "0.5").replace('&frac14;', "0.25").replace('&frac34;', "0.75")
            try:
                amount, unit, ingredient, note = parse_single_ingredient(x)
                if ingredient:
                    ingredient_list.append(
                        {
                            'amount': amount,
                            'unit': {
                                'text': unit,
                                'id': random.randrange(10000, 99999)
                            },
                            'ingredient': {
                                'text': ingredient,
                                'id': random.randrange(10000, 99999)
                            },
                            'note': note,
                            'original': x
                        }
                    )
            except Exception:
                ingredient_list.append(
                    {
                        'amount': 0,
                        'unit': {
                            'text': '',
                            'id': random.randrange(10000, 99999)
                        },
                        'ingredient': {
                            'text': x,
                            'id': random.randrange(10000, 99999)
                        },
                        'note': '',
                        'original': x
                    }
                )

            ingredients = ingredient_list
        else:
            ingredients = []
    return ingredients


def parse_instructions(instructions):
    instruction_text = ''

    # flatten instructions if they are in a list
    if type(instructions) == list:
        for i in instructions:
            if type(i) == str:
                instruction_text += i
            else:
                if 'text' in i:
                    instruction_text += i['text'] + '\n\n'
                elif 'itemListElement' in i:
                    for ile in i['itemListElement']:
                        if type(ile) == str:
                            instruction_text += ile + '\n\n'
                        elif 'text' in ile:
                            instruction_text += ile['text'] + '\n\n'
                else:
                    instruction_text += str(i)
        instructions = instruction_text

    instructions = re.sub(r'\n\s*\n', '\n\n', instructions)
    instructions = re.sub(' +', ' ', instructions)
    instructions = re.sub('</p>', '\n', instructions)
    instructions = re.sub('<[^<]+?>', '', instructions)
    return normalize_string(instructions)


def parse_image(image):
    # check if list of images is returned, take first if so
    if type(image) == list:
        for pic in image:
            if (type(pic) == str) and (pic[:4] == 'http'):
                image = pic
            elif 'url' in pic:
                image = pic['url']
    elif type(image) == dict:
        if 'url' in image:
            image = image['url']

    # ignore relative image paths
    if image[:4] != 'http':
        image = ''
    return image


def parse_servings(servings):
    if type(servings) == str:
        try:
            servings = int(re.search(r'\d+', servings).group())
        except AttributeError:
            servings = 1
    elif type(servings) == list:
        try:
            servings = int(re.findall(r'\b\d+\b', servings[0])[0])
        except KeyError:
            servings = 1
    return servings


def parse_cooktime(cooktime):
    if type(cooktime) not in [int, float]:
        try:
            cooktime = float(re.search(r'\d+', cooktime).group())
        except (ValueError, AttributeError):
            try:
                cooktime = round(iso_parse_duration(cooktime).seconds / 60)
            except ISO8601Error:
                try:
                    if (type(cooktime) == list and len(cooktime) > 0):
                        cooktime = cooktime[0]
                    cooktime = round(parse_duration(cooktime).seconds / 60)
                except AttributeError:
                    cooktime = 0

    return cooktime


def parse_preptime(preptime):
    if type(preptime) not in [int, float]:
        try:
            preptime = float(re.search(r'\d+', preptime).group())
        except ValueError:
            try:
                preptime = round(iso_parse_duration(preptime).seconds / 60)
            except ISO8601Error:
                try:
                    if (type(preptime) == list and len(preptime) > 0):
                        preptime = preptime[0]
                    preptime = round(parse_duration(preptime).seconds / 60)
                except AttributeError:
                    preptime = 0

    return preptime


def parse_keywords(keyword_json, space):
    keywords = []
    # keywords as list
    for kw in keyword_json:
        kw = normalize_string(kw)
        if k := Keyword.objects.filter(name=kw, space=space).first():
            keywords.append({'id': str(k.id), 'text': str(k)})
        else:
            keywords.append({'id': random.randrange(1111111, 9999999, 1), 'text': kw})

    return keywords


def listify_keywords(keyword_list):
    # keywords as string
    try:
        if type(keyword_list[0]) == dict:
            return keyword_list
    except (KeyError, IndexError):
        pass
    if type(keyword_list) == str:
        keyword_list = keyword_list.split(',')

    # keywords as string in list
    if (type(keyword_list) == list and len(keyword_list) == 1 and ',' in keyword_list[0]):
        keyword_list = keyword_list[0].split(',')
    return [x.strip() for x in keyword_list]


def normalize_string(string):
    # Convert all named and numeric character references (e.g. &gt;, &#62;)
    unescaped_string = unescape(string)
    unescaped_string = re.sub('<[^<]+?>', '', unescaped_string)
    unescaped_string = re.sub(' +', ' ', unescaped_string)
    unescaped_string = re.sub('</p>', '\n', unescaped_string)
    unescaped_string = re.sub(r'\n\s*\n', '\n\n', unescaped_string)
    unescaped_string = unescaped_string.replace("\xa0", " ").replace("\t", " ").strip()
    return unescaped_string
