import argparse
from PIL import Image
from resizeimage import resizeimage
import pathlib
from multiprocessing import Pool, cpu_count
import time
import shutil


class ProgressBar:

    def __init__(self, end=100):
        self.end = end
        self.current = 0

    def on_result(self, result):
        self.next()
        self.print_progress()

    def next(self):
        self.current += 1

    def print_progress(self, length=100, fill='█', autosize=True):
        percent = "{0:.1f}".format(100 * (self.current / float(self.end)))
        styling = '%s/%s |%s| %s%%' % (self.current, self.end, fill, percent)
        if autosize:
            cols, _ = shutil.get_terminal_size(fallback=(length, 1))
            length = cols - len(styling)
        filled_length = int(length * self.current // self.end)
        bar = fill * filled_length + '-' * (length - filled_length)
        print('\r%s' % styling.replace(fill, bar), end='\r')
        # Print New Line on Complete
        if self.current == self.end:
            print()


def open_dir(path):
    directory = pathlib.Path(path)
    if directory.is_dir():
        return directory
    raise argparse.ArgumentTypeError("File '{0}' doesn't exist or isn't a directory".format(path))


def open_file(path):
    file = pathlib.Path(path)
    if file.is_file():
        return file
    raise argparse.ArgumentTypeError("File '{0}' doesn't exist or isn't a file".format(path))


def worker(path, directory, outdir, width, height, verbose):
    resize_image(path, directory, outdir, width=width, height=height, verbose=verbose)


def resize_dir(directory: pathlib.Path, outdir: pathlib.Path, recursive=False, width=None, height=None, ext="jpg",
               no_progress=False, verbose=False):
    if verbose:
        print("Searching {0}{1} files in directory {2}"
              .format("recursively " if recursive else "", ext, directory.resolve()))
    if recursive:
        generator = directory.glob('**/*.{0}'.format(ext))
    else:
        generator = directory.glob('*.{0}'.format(ext))

    paths = []
    for path in generator:
        paths.append(path)

    total = len(paths)
    print("{0} image{1} to resize".format(total, "s" if total > 1 else ""))
    response = input("Continue ? (Y/n)")

    if response.lower() not in ["y", "yes"]:
        print("Canceled.")
    else:
        if no_progress:
            cb = None
        else:
            progress = ProgressBar(end=total)
            cb = progress.on_result

        if verbose:
            print("Starting files process")

        start = time.time()

        p = Pool(cpu_count())
        for path in paths:
            p.apply_async(worker, args=(path, directory, outdir, width, height, verbose), callback=cb)
        p.close()
        p.join()
        end = time.time()
        print("Took {0:.2f} sec.".format(end - start))


def resize_image(file: pathlib.Path, indir: pathlib.Path, outdir: pathlib.Path, width=None, height=None, verbose=False):
    assert width or height, "At least height or width must be specified"

    if verbose:
        print("Opening file {}".format(file))

    with Image.open(file.resolve()) as img:
        if width and height:
            resized = resizeimage.resize_thumbnail(img, [width, height])
        elif width:
            resized = resizeimage.resize_width(img, width)
        else:
            resized = resizeimage.resize_height(img, height)

        if verbose:
            print("File {} resized. Will save it.".format(file))

        final_path = file.relative_to(indir)
        final_path = outdir.joinpath(final_path)
        if not final_path.parent.exists():
            final_path.parent.mkdir(parents=True)
        resized.save(final_path, resized.format)

        if verbose:
            print("Saved resized version of {} to {}".format(file, final_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
        Resize image(s) to given dimension.
        To resize image(s) you must specify at least one of --width and --height and specify one
        of --file (for single image) or --dir (for all images in the directory).
        All resized images will be output on the directory specified by --outdir, this argument is
        mandatory.
    """)

    parser.add_argument('--width', type=int, help="the maximum width for the resized image")
    parser.add_argument('--height', type=int, help="the maximum height for the resized image")
    parser.add_argument('-d', '--dir', type=open_dir, help="the directory to find images in")
    parser.add_argument('-r', '--recursive', const=True, action='store_const', default=False,
                        help="iterates over directory recursively (default: %(default)s)")
    parser.add_argument('-f', '--file', type=open_file, help="the image to resize")
    parser.add_argument('-o', '--outdir', type=open_dir, help="the directory to put the resized files in (mandatory)",
                        required=True)
    parser.add_argument('--ext', type=str, default="jpg",
                        help="The image extension (ex: jpg, jpeg, png, ...). (default: %(default)s)")
    parser.add_argument("--no-progress", default=False, action="store_const", const=True,
                        help="if specified, progress bar won't be displayed (default: %(default)s)")
    parser.add_argument("-v", "--verbose", action="store_const", const=True, default=False,
                        help="if specified, set the program verbose (default: %(default)s)")

    args = parser.parse_args()
    if not (args.width or args.height):
        parser.error('Specify at least --width or --height arguments (both can be specified)')

    if not (args.dir or args.file):
        parser.error('Specify one of --dir and --file arguments')

    if args.dir and args.file:
        parser.error('You must choose between --dir and --file')

    if args.dir:
        resize_dir(args.dir, args.outdir, recursive=args.recursive, width=args.width, height=args.height, ext=args.ext,
                   no_progress=args.no_progress, verbose=args.verbose)
    else:
        resize_image(args.file, pathlib.Path('.'), args.outdir, width=args.width, height=args.height,
                     verbose=args.verbose)
