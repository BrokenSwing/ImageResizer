import argparse
from PIL import Image
from resizeimage import resizeimage
import pathlib
from multiprocessing import Pool, cpu_count
import time


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


def worker(arguments):
    path, directory, outdir, width, height = arguments
    resize_image(path, directory, outdir, width=width, height=height)


def resize_dir(directory: pathlib.Path, outdir: pathlib.Path, recursive=False, width=None, height=None, ext="jpg"):
    if recursive:
        generator = directory.glob('**/*.{0}'.format(ext))
    else:
        generator = directory.glob('*.jpg')

    paths = []
    for path in generator:
        paths.append(path)

    total = len(paths)
    print("{0} image{1} to resize".format(total, "s" if total > 1 else ""))
    response = input("Continue ? (Y/n)")

    if response.lower() not in ["y", "yes"]:
        print("Canceled.")
    else:
        start = time.time()
        exp = []
        for path in paths:
            exp.append([path, directory, outdir, width, height])
        with Pool(cpu_count()) as p:
            p.map(worker, exp)

        end = time.time()
        print("Took {0:.2f} sec.".format(end - start))


def resize_image(file: pathlib.Path, indir: pathlib.Path, outdir: pathlib.Path, width=None, height=None):
    assert width or height, "At least height or width must be specified"

    with Image.open(file.resolve()) as img:
        if width and height:
            resized = resizeimage.resize_contain(img, [width, height])
        elif width:
            resized = resizeimage.resize_width(img, width)
        else:
            resized = resizeimage.resize_crop(img, height)
        final_path = file.relative_to(indir)
        final_path = outdir.joinpath(final_path)
        if not final_path.parent.exists():
            final_path.parent.mkdir(parents=True)
        resized.save(final_path, resized.format)


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
    parser.add_argument('-o', '--outdir', type=open_dir, help="The directory to put the resized files in (mandatory)",
                        required=True)
    parser.add_argument('--ext', type=str, default="jpg",
                        help="The image extension (ex: jpg, jpeg, png, ...). (default: %(default)s)")

    args = parser.parse_args()
    if not (args.width or args.height):
        parser.error('Specify at least --width or --height arguments (both can be specified)')

    if not (args.dir or args.file):
        parser.error('Specify one of --dir and --file arguments')

    if args.dir and args.file:
        parser.error('You must choose between --dir and --file')

    if args.dir:
        resize_dir(args.dir, args.outdir, recursive=args.recursive, width=args.width, height=args.height, ext=args.ext)
    else:
        resize_image(args.file, pathlib.Path('.'), args.outdir, width=args.width, height=args.height)
