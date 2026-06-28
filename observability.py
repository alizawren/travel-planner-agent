try:
    from traceloop.sdk.decorators import task, workflow
except ImportError:

    def task(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]

        def decorator(fn):
            return fn

        return decorator

    def workflow(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]

        def decorator(fn):
            return fn

        return decorator
