import functools
import inspect
import hashlib
import pickle
from redis.asyncio import Redis
from typing import Any, Callable, Optional


def cached(ttl: int = 300, prefix: Optional[str] = None):
    """
    Декоратор для кэширования результатов методов

    Поддерживает:
    - Методы с user_id: ключ = prefix:user_id
    - Методы с одним строковым аргументом: ключ = prefix:значение
    - Методы с несколькими аргументами: ключ = prefix:hash
    - Методы без аргументов: ключ = prefix
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'cache_manager') or self.cache_manager is None:
                return await func(self, *args, **kwargs)

            key_prefix = prefix or func.__name__
            cache_key = _generate_cache_key(key_prefix, func, args, kwargs)

            cached_value = await self.cache_manager.get(cache_key)
            if cached_value:
                return pickle.loads(cached_value)

            result = await func(self, *args, **kwargs)

            if result is not None:
                await self.cache_manager.setex(cache_key, ttl, pickle.dumps(result))

            return result

        return wrapper

    return decorator


def invalidates(*patterns: str):
    """
    Декоратор для инвалидации кэша после выполнения метода

    Поддерживает:
    - Точные ключи: "user:{user_id}"
    - Паттерны с *: "users_list:*"
    - Автоматически определяет тип
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'cache_manager') or self.cache_manager is None:
                return await func(self, *args, **kwargs)

            # Получаем значения аргументов для подстановки
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()

            for pattern in patterns:
                try:
                    # Подставляем аргументы
                    formatted = pattern.format(**bound_args.arguments)

                    # Удаляем кэш
                    await _invalidate_cache(self.cache_manager, formatted)

                except KeyError:
                    # Если аргумент не найден, пробуем удалить как есть
                    await _invalidate_cache(self.cache_manager, pattern)
                except Exception as e:
                    print(f"Cache invalidation error for {pattern}: {e}")

            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


def _generate_cache_key(prefix: str, func: Callable, args: tuple, kwargs: dict) -> str:
    """Универсальная генерация ключа кэша"""

    # 1. Пытаемся найти user_id
    user_id = _extract_arg('user_id', args, kwargs)
    if user_id is not None and isinstance(user_id, int):
        return f"{prefix}:{user_id}"

    # 2. Пытаемся найти promo (или любой другой строковый аргумент)
    string_arg = _find_string_arg(func, args, kwargs)
    if string_arg is not None:
        return f"{prefix}:{string_arg}"

    # 3. Если нет аргументов
    if len(args) == 0 and len(kwargs) == 0:
        return prefix

    # 4. В остальных случаях - хэш
    args_str = str(args) + str(sorted(kwargs.items()))
    args_hash = hashlib.md5(args_str.encode()).hexdigest()
    return f"{prefix}:{args_hash}"


def _extract_arg(arg_name: str, args: tuple, kwargs: dict) -> Any:
    """Извлечь аргумент по имени из args или kwargs"""
    if arg_name in kwargs:
        return kwargs[arg_name]

    # Получаем имена параметров функции через inspect
    # Для упрощения: если первый аргумент и он подходит по типу
    if len(args) > 0:
        return args[0]

    return None


def _find_string_arg(func: Callable, args: tuple, kwargs: dict) -> Optional[str]:
    """Найти одиночный строковый аргумент"""

    # Проверяем kwargs
    if len(kwargs) == 1:
        value = next(iter(kwargs.values()))
        if isinstance(value, str):
            return value

    # Проверяем args
    if len(args) == 1 and isinstance(args[0], str):
        return args[0]

    return None


async def _invalidate_cache(cache_manager, key_or_pattern: str):
    """Универсальная инвалидация кэша"""

    # Если есть * - удаляем по паттерну
    if '*' in key_or_pattern:
        await cache_manager.delete_pattern(key_or_pattern)
        return

    # Пробуем удалить точный ключ
    if await cache_manager.exists(key_or_pattern):
        await cache_manager.delete(key_or_pattern)
        return

    # Если точного ключа нет, пробуем удалить как паттерн с *
    pattern = f"{key_or_pattern}:*"
    keys = await cache_manager.keys(pattern)
    if keys:
        await cache_manager.delete(*keys)
        return

    # Пробуем удалить как паттерн без ничего
    pattern = f"{key_or_pattern}*"
    keys = await cache_manager.keys(pattern)
    if keys:
        await cache_manager.delete(*keys)


class CacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, key: str):
        return await self.redis.get(key)

    async def setex(self, key: str, ttl: int, value: bytes):
        await self.redis.setex(key, ttl, value)

    async def exists(self, key: str):
        return await self.redis.exists(key)

    async def delete(self, *keys):
        if keys:
            await self.redis.delete(*keys)

    async def keys(self, pattern: str):
        return await self.redis.keys(pattern)

    async def delete_pattern(self, pattern: str):
        """Удалить все ключи по паттерну"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)