# IRTrackingDLL

This is an adaptation version of [DINO-DLL](https://github.com/HL2-DINO/DINO-DLL), for citation information, see the original project. The original readme file is in [README-Raw.md](README-Raw.md).

## Build Outputs

This project builds a Windows Runtime Component for HoloLens 2 / UWP use. After building the `Release|ARM64` configuration, the main exported files are generated under:

```text
ARM64/Release/HL2DinoPlugin/
```

The two files normally needed by a Unity C# project are:

- `HL2DinoPlugin.dll`: the native C++/WinRT implementation. It contains the Research Mode access, IR image processing, tool tracking logic, and the exported runtime class implementation.
- `HL2DinoPlugin.winmd`: the Windows Metadata file. C# / Unity uses this metadata to discover the WinRT class and callable methods, such as `Get16BitDepthImageBuf()`, `Get16BitABImageBuf()`, `GetDepthToWorldMatrix()`, and `GetDepthPixelWorldCoordinate(...)`.

For Unity, copy the generated `.dll` and `.winmd` into:

```text
Assets/Plugins/WSA
```

For HoloLens 2 deployment, build with `Release` and `ARM64`.

## Automated Build Script

The repository includes [build.py](build.py), a small Python build helper that restores NuGet packages and builds the Visual Studio solution without hard-coding a compiler or MSBuild path.

Prerequisites:

- Windows with Visual Studio 2019 or Visual Studio 2022.
- Visual Studio C++ build tools, including the MSVC toolchain.
- Universal Windows Platform development tools.
- A Windows 10 SDK installed through Visual Studio. This project has also built successfully with newer Windows SDK versions.
- Python 3 available from the command line as `python`.

Run the default build from the repository root:

```powershell
python .\build.py
```

By default, this restores NuGet packages and builds:

```text
Release|ARM64
```

The script looks for `MSBuild.exe` in this order:

1. The `MSBUILD_EXE` environment variable, if set.
1. `MSBuild.exe` on `PATH`.
1. Visual Studio's `vswhere.exe`, which is used to locate the latest installed Visual Studio MSBuild.

Useful options:

```powershell
python .\build.py --no-restore
python .\build.py --configuration Debug --platform x64
python .\build.py -c Release -p ARM64 -s HL2DinoPlugin.sln
```

After a successful default build, the DLL and winmd are available under:

```text
ARM64/Release/HL2DinoPlugin/
```

## Sensor Image Buffers

The plugin exposes raw 16-bit buffers from the HoloLens 2 AHAT depth sensor.

### `GetRawDepthImageBuffer()`

`GetRawDepthImageBuffer()` returns a `UInt16[]` copy of the latest raw AHAT depth frame. Each element corresponds to one pixel in the 512 x 512 AHAT depth image, in row-major order.

The values have the same meaning as `Get16BitDepthImageBuf()`:

- `0`: no valid depth was returned for that pixel.
- `1..4090`: valid depth in millimetres, as used by the tracking code.
- `>4090`: treated by this project as invalid / wrap-around depth data for AHAT depth processing.

This is the original raw-depth getter kept for compatibility with existing consumers. Use `Get16BitDepthImageBuf()` when you prefer the newer name that explicitly describes the 16-bit buffer.

### `GetRawABImageBuffer()`

`GetRawABImageBuffer()` returns a `UInt16[]` copy of the latest raw AHAT active-brightness frame. Each element corresponds to one pixel in the 512 x 512 AHAT image, in row-major order.

The values have the same meaning as `Get16BitABImageBuf()`: they are infrared / active-brightness response intensities from the depth sensor, not distance values. Brighter IR-reflective regions usually produce larger values.

This is the original raw active-brightness getter kept for compatibility with existing consumers. Use `Get16BitABImageBuf()` when you prefer the newer name that explicitly describes the 16-bit buffer.

### `Get16BitDepthImageBuf()`

`Get16BitDepthImageBuf()` returns a `UInt16[]` copy of the latest raw AHAT depth frame. Each element corresponds to one pixel in the 512 x 512 AHAT depth image, in row-major order.

The value is the sensor-provided depth value in millimetres:

- `0`: no valid depth was returned for that pixel.
- `1..4090`: valid depth in millimetres, as used by the tracking code.
- `>4090`: treated by this project as invalid / wrap-around depth data for AHAT depth processing.

Use this buffer when you need metric depth values for analysis, custom processing, or your own visualization.

### `Get16BitABImageBuf()`

`Get16BitABImageBuf()` returns a `UInt16[]` copy of the latest raw AHAT active-brightness frame. Each element corresponds to one pixel in the 512 x 512 AHAT image, in row-major order.

The value is an infrared / active-brightness response intensity from the depth sensor, not a distance measurement:

- Larger values mean the pixel received a stronger active-brightness / infrared response.
- Lower values mean a weaker response or background.
- Bright IR-reflective markers usually appear as high-response regions in this buffer.

This buffer is useful if you want the original 16-bit IR response for thresholding, marker detection, debugging, or offline analysis.

## Depth Camera Pose

### `GetDepthToWorldMatrix()`

`GetDepthToWorldMatrix()` returns a `Double[]` containing the latest 4 x 4 transform matrix from the AHAT depth-camera coordinate frame to the externally supplied world/reference coordinate frame.

The returned array contains 16 values in column-major order, matching Eigen's default storage order and the existing tool-pose matrix output convention. Conceptually, it is the same matrix passed internally as `inDepth2World` during marker validation:

```text
pointInWorld = depthToWorld * pointInDepth
```

The matrix is updated once per processed depth frame after the HoloLens spatial locator successfully resolves the headset pose for that frame timestamp. Before the depth sensor loop has produced a valid located frame, this method returns an empty array.

This transform is built from:

1. The fixed AHAT depth-camera extrinsics from Research Mode.
1. The per-frame HoloLens rig pose from the spatial locator.
1. The reference coordinate system previously supplied through `SetReferenceCoordinateSystem(...)`, or the default stationary frame if none was supplied.

Use this interface when Unity or another consumer needs to transform raw depth-camera points into the same world frame used by the plugin's tracking output.

### `GetDepthPixelWorldCoordinate(Single pixelX, Single pixelY, UInt16 depthValue)`

`GetDepthPixelWorldCoordinate(...)` returns a `Double[]` containing the world-frame 3D coordinate for one depth-image pixel and its raw depth value.

Inputs:

- `pixelX`: pixel x coordinate in the AHAT depth image.
- `pixelY`: pixel y coordinate in the AHAT depth image.
- `depthValue`: raw 16-bit depth value at that pixel, in millimetres.

The returned array contains three values:

```text
[x, y, z]
```

The values are in metres and use the same world/reference coordinate frame as `GetDepthToWorldMatrix()` and the plugin's tracked tool pose output.

Internally, the function:

1. Uses Research Mode's `MapImagePointToCameraUnitPlane(...)` to convert the pixel coordinate into a depth-camera ray.
1. Scales that ray by `depthValue / 1000.0` to obtain a 3D point in the depth-camera coordinate frame.
1. Applies the latest cached depth-to-world matrix to transform the point into the world/reference frame.

The function returns an empty array if the depth camera is unavailable, if `depthValue` is `0` or greater than `4090`, if the pixel cannot be mapped by Research Mode, or if no valid depth-to-world matrix has been cached yet.
