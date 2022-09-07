import argparse
import datetime
import glob
import os
import sys
import Metashape
import Metashape, statistics


# Class to automate Agisoft Metashape processing
#
# This automates the processing with the following assumed project structure:
# _base_path_:
#  Root location for the project. This is where the image folder is assumed
#  under 'images' unless given with a different relative path location.
#
#  The Agisoft project file will be saved under this location along with the
#  project report that is created at the end.
#
#  For setting the reference a file with the name 'images_metadata.csv' is
#  assumed under here as well. The sequence for the fields should be:
#  file_name, lon, lat, elevation, yaw, pitch, roll
#
class Agisoft:
    EXPORT_IMAGE_TYPE = '.tif'
    IMPORT_IMAGE_TYPE = '.JPG'
    PROJECT_TYPE = '.psx'
    PROJECT_REPORT = '.pdf'
    REFERENCE_FILE = 'images_metadata_gps.csv'


    WGS_84 = Metashape.CoordinateSystem("EPSG::4326")
    v_projection = WGS_84
    projection = Metashape.OrthoProjection()
    projection.crs=v_projection
    compression = Metashape.ImageCompression()
    compression.tiff_big = True


    #UTM_CA = Metashape.CoordinateSystem("EPSG::32611")
    #UTM_CO = Metashape.CoordinateSystem("EPSG::32613")
    X_1M_IN_DEG = 1.13747e-05  # 1m in degree using EPSG:4326
    Y_1M_IN_DEG = 9.0094e-06   #
    X_5M_IN_DEG = 5.76345e-05  # 5m in degree using EPSG:4326
    Y_5M_IN_DEG = 4.50396e-05  #

    IMAGE_ACCURACY_MATCHING = 0
# changed in 1.6 hightest = 0, high=1,medium =2,low=4,lowest=8

    KEYPOINT_LIMIT = 40000
    TIEPOINT_LIMIT = 0

    REPROJECTION_ERROR_THRESHOLD = 0.3
    REPROJECTION_ACCURACY_THRESHOLD = 10

    DENSE_POINT_QUALITY = dict(
        ultra= 1,
        high=2,
        medium=4,
        low=8,
        lowest=16
    )



    def __init__(self, options):
        # Ensure trailing slash
        self.project_base_path = os.path.join(options.base_path, '')
        self.continue_proj = options.continue_proj
        self.project_file_name = self.project_file_path(options.project_name)

        self.test_area = options.test_area

        self.setup_application()

        self.create_new_project()
        self.project = Metashape.app.document
        self.project.open(self.project_file_name + self.PROJECT_TYPE,read_only=False)
        self.project.read_only = False

        self.chunk = self.project.chunk

        self.setup_camera()

        self.image_folder = os.path.join(
            self.project_base_path, options.image_folder, ''
        )
        self.image_type = options.image_type

    def create_new_project(self):
        if not os.path.exists(path=self.project_file_name + self.PROJECT_TYPE):
            new_project = Metashape.Document()
            chunk = new_project.addChunk()
            new_project.save(
                path=self.project_file_name + self.PROJECT_TYPE,
                chunks=[chunk]
            )

    def project_file_path(self, project_name):
        run_date = datetime.date.today().strftime('%Y_%m_%d')
        project_name = project_name + '_' + run_date
        if len(self.continue_proj) > 0:
            project_name = self.continue_proj
        return os.path.join(
            self.project_base_path, project_name
        )

    def setup_application(self):
        app = Metashape.Application()
        # Use all available GPUs, needs a bit mask
        number_of_gpus = len(Metashape.app.enumGPUDevices())
        mask = int(str('1' * number_of_gpus).rjust(8, '0'), 2)
        app.gpu_mask = mask
        # Allow usage of CPU and GPU
        app.cpu_enable = True

        settings = Metashape.Application.Settings()
        # Logging
        settings.log_enable = True
        settings.log_path = self.project_file_name + '_agisoft.log'
        settings.save()

    def setup_camera(self):
        # Imported camera coordinates projection
        self.chunk.crs = self.WGS_84
        # Accuracy for camera position in m
        self.chunk.camera_location_accuracy = Metashape.Vector([1, 1, 1])
        # Accuracy for camera orientations in degree
        self.chunk.camera_rotation_accuracy = Metashape.Vector([1, 1, 1])

    def save_and_exit(self):
        self.project.save()
        sys.exit(-1)

    def image_list(self):
        images = glob.glob(
            self.image_folder + '**/*' + self.image_type, recursive=True
        )
        if len(images) == 0:
            print('**** EXIT - ' + self.image_type +
                  ' no files found in directory:')
            print('    ' + self.image_folder)
            self.save_and_exit()
        else:
            return images

    def check_reference_file(self, file):
        """
        Check that the given reference file exists and has the image types
        loaded with this project by comparing file endings.
        """
        if os.path.exists(file):
            with open(file) as file:
                next(file)  # skip header line
                first_file = next(file).split(',')[0]
                if not first_file.endswith(self.image_type):
                    print('**** Reference file has different '
                          'source image types *****\n'
                          '   given: ' + self.image_type + '\n'
                          '   first image: ' + first_file)
                    self.save_and_exit()
        else:
            print('**** EXIT - No reference file found ****')
            self.save_and_exit()

    def load_image_references(self):
        reference_file = self.project_base_path + self.REFERENCE_FILE
        self.check_reference_file(reference_file)
        self.chunk.importReference(
            path=reference_file,
            delimiter=',',
            format=Metashape.ReferenceFormatCSV,
        )

    def align_images(self):
        self.chunk.addPhotos(self.image_list())
        self.load_image_references()
        self.chunk.matchPhotos(
            downscale= self.IMAGE_ACCURACY_MATCHING,
            generic_preselection=True,
            reference_preselection=True,
            keypoint_limit=self.KEYPOINT_LIMIT,
            tiepoint_limit=self.TIEPOINT_LIMIT,
        )
        self.chunk.alignCameras()
        self.project.save()

    def remove_by_criteria(self, criteria, threshold):
        point_cloud_filter = Metashape.PointCloud.Filter()
        point_cloud_filter.init(self.chunk, criterion=criteria)
        point_cloud_filter.removePoints(threshold)

    def filter_sparse_cloud(self):
        # Points that statistical error in point placement exceed threshold
        self.remove_by_criteria(
            Metashape.PointCloud.Filter.ReprojectionError,
            self.REPROJECTION_ERROR_THRESHOLD,
        )
        self.chunk.optimizeCameras()
        # Points that accuracy of point placement from local neighbor points
        # exceed threshold
        self.remove_by_criteria(
            Metashape.PointCloud.Filter.ProjectionAccuracy,
            self.REPROJECTION_ACCURACY_THRESHOLD,
        )
        self.chunk.optimizeCameras()

    def build_dense_cloud(self, dense_cloud_quality):
        self.chunk.buildDepthMaps(
            downscale=self.DENSE_POINT_QUALITY.get(dense_cloud_quality, 'high'),
            filter_mode=Metashape.AggressiveFiltering,
        )
        #self.project.save()
        self.chunk.buildDenseCloud()
        #self.project.save()


    def export_results(self):
        self.chunk.exportRaster(
            path=self.project_file_name + '_dem' + self.EXPORT_IMAGE_TYPE,
            source_data=Metashape.DataSource.ElevationData,
            projection = self.projection,
            image_format=Metashape.ImageFormat.ImageFormatTIFF)

        self.chunk.exportRaster(
            path=self.project_file_name + self.EXPORT_IMAGE_TYPE,
            image_compression = self.compression,
            source_data=Metashape.DataSource.OrthomosaicData,
            projection = self.projection,
            image_format=Metashape.ImageFormat.ImageFormatTIFF)

        #self.chunk.exportReport(self.project_file_name + self.PROJECT_REPORT)


    def resize_region(self):
        def cross(a, b):
            result = Metashape.Vector([a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y - a.y *b.x])
            return result.normalized()

        BUFFER = 10 #percent
        new_region = Metashape.Region()
        xcoord = Metashape.Vector([10E10, -10E10])
        ycoord = Metashape.Vector([10E10, -10E10])
        avg = [[],[]]
        T = self.chunk.transform.matrix
        s = self.chunk.transform.matrix.scale()

        crs = self.chunk.crs
        z = Metashape.Vector([0,0])

        for camera in self.chunk.cameras:
            if camera.transform:
                coord = crs.project(T.mulp(camera.center))
                xcoord[0] = min(coord.x, xcoord[0])
                xcoord[1] = max(coord.x, xcoord[1])
                ycoord[0] = min(coord.y, ycoord[0])
                ycoord[1] = max(coord.y, ycoord[1])
                z[0] += coord.z
                z[1] += 1
                avg[0].append(coord.x)
                avg[1].append(coord.y)
        z = z[0] / z[1]

        #print(str(xcoord[0]))
        #print(str(xcoord[1]))
        #print(str(ycoord[0]))
        #print(str(ycoord[1]))
        if self.test_area:
            xcoord[0] = -76.402939
            ycoord[0] = -0.683361
            xcoord[1] = -76.402053
            ycoord[1] = -0.682436
        #else:
        #    xcoord[0] = -76.40431935
        #    ycoord[0] = -0.685626081
        #    xcoord[1] = -76.39980838
        #    ycoord[1] = -0.681057872


        avg = Metashape.Vector([statistics.median(avg[0]), statistics.median(avg[1]), z])
        corners = [Metashape.Vector([xcoord[0], ycoord[0], z]),
        			Metashape.Vector([xcoord[0], ycoord[1], z]),
        			Metashape.Vector([xcoord[1], ycoord[1], z]),
        			Metashape.Vector([xcoord[1], ycoord[0], z])]

        corners = [T.inv().mulp(crs.unproject(x)) for x in list(corners)]


        side1 = corners[0] - corners[1]
        side2 = corners[0] - corners[-1]
        side1g = T.mulp(corners[0]) - T.mulp(corners[1])
        side2g = T.mulp(corners[0]) - T.mulp(corners[-1])
        side3g = T.mulp(corners[0]) - T.mulp(Metashape.Vector([corners[0].x, corners[0].y, 0]))
        new_size = ((100 + BUFFER) / 100) * Metashape.Vector([side2g.norm()/s, side1g.norm()/s, 3*side3g.norm() / s]) ##

        xcoord, ycoord, z = T.inv().mulp(crs.unproject(Metashape.Vector([sum(xcoord)/2., sum(ycoord)/2., z - 2 * side3g.z]))) #
        new_center = Metashape.Vector([xcoord, ycoord, z]) #by 4 corners

        horizontal = side2
        vertical = side1
        normal = cross(vertical, horizontal)
        horizontal = -cross(vertical, normal)
        vertical = vertical.normalized()

        R = Metashape.Matrix ([horizontal, vertical, -normal])
        new_region.rot = R.t()

        new_region.center = new_center
        new_region.size = new_size
        self.chunk.region = new_region


    def process(self, options):
        
        self.project.save()
        if options.step_one_align == False and options.step_two_dense_cloud == False:
            print("No processing step selected. Choos step one or two")
        
        if options.step_one_align:
            self.align_images()
            self.filter_sparse_cloud()
            print("Done filtering the sparse cloud")
            self.project.save()
            self.chunk.buildModel(source_data=Metashape.PointCloudData)
            self.chunk.reduceOverlap(overlap = 6)
            print("done reducing overlap")
            #self.resize_region()
        	#print("Done resizing the region")
            # self.project.save()
                
        if options.step_two_dense_cloud:
            print("building dense cloud")
            self.build_dense_cloud(options.dense_cloud_quality)
            print("building DEM")
            self.chunk.buildDem()
            print("building Orthomosaic")
            self.chunk.buildOrthomosaic(surface_data=Metashape.DataSource.ElevationData)
            self.project.save()

        if options.with_export:
            self.export_results()


parser = argparse.ArgumentParser()
parser.add_argument(
    '--base-path', help='Root directory of the project.', required=True
)
parser.add_argument('--project-name', help='Name of project.', required=True)
parser.add_argument(
    '--image-folder',
    help='Location of images relative to base-path.',
    default='images'
)
parser.add_argument(
    '--image-type',
    help='Type of images - default to .tif',
    default=Agisoft.IMPORT_IMAGE_TYPE,
)
parser.add_argument(
    '--dense-cloud-quality', type=str, required=False, default='high',
    help='Overwrite default dense point cloud quality (High).'
)
parser.add_argument(
    '--with-export', type=bool, required=False, default=False,
    help='Export DEM, Orthomosaic and PDF report after dense cloud'
)

parser.add_argument(
    '--step-one-align', type=bool, required=False, default=False,
    help='proceed with first step of processing, aligning photos and filtering sparse cloud'
)

parser.add_argument(
    '--step-two-dense-cloud', type=bool, required=False, default=False,
    help='proceed with second step of processing, build dense cloud, DEM and Orthomosaic'
)


parser.add_argument(
    '--continue-proj', type=str, required=False, default='',
    help='prelative path of previous project'
)

parser.add_argument(
    '--test-area', type=bool, required=False, default=False,
    help='resize to 100 meter grid for testing'
)



# On chpc we created a symbolic link between metashape and photscan. In theory one should call photoscan.sh -r etc NOT metashape.sh -r

# ﻿# Example command line execution:
# Mac OS:
# ./PhotoScanPro -r agisoft_workflow.py --base-path /path/to/root/project/directory --project-name test
#
# Windows:
# .\photoscan.exe -r agisoft_workflow.py --base-path D:\path/to/root/project/direcotry --project-name test
#
# Linux (headless):
# photoscan.sh -platform offscreen -r agisoft_workflow.py --base_path /path/to/root/project/directory -- project-name test
# Optional arguments are:
# _image_folder_: Name and relative location where images are
# _image_type_: TYpe of images (i.e. .jpg, .iiq)
#
if __name__ == '__main__':
    arguments = parser.parse_args()
    project = Agisoft(arguments)
project.process(arguments)
