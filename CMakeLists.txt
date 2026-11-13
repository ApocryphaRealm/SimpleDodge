cmake_minimum_required(VERSION 3.21)

# Simple Dodge - an SKSE dodge plugin for Skyrim SE / AE (and Skyrim 1.7 on the second build line),
# built with CMake + vcpkg CommonLibSSE-NG. GPL-3.0-or-later; NOTICE.md credits the code it is based on.
project(
	SimpleDodge
	VERSION 1.3.0
	LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# IPO/LTCG off: with MSVC 14.52 (2026-11-12) /GL+/LTCG output is flagged by the Bitdefender engine family on VirusTotal (Gen:Variant.Ulise.617802) and Nexus quarantines it; IPO off scans clean
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION OFF)
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_DEBUG OFF)

configure_file(
	${CMAKE_CURRENT_SOURCE_DIR}/cmake/version.rc.in
	${CMAKE_CURRENT_BINARY_DIR}/version.rc
	@ONLY
)

file(GLOB_RECURSE headers CONFIGURE_DEPENDS "include/*.h" "src/*.h")
file(GLOB_RECURSE sources CONFIGURE_DEPENDS "src/*.cpp")

source_group(TREE ${CMAKE_CURRENT_SOURCE_DIR} FILES ${headers} ${sources})

find_package(CommonLibSSE CONFIG REQUIRED)
find_package(spdlog REQUIRED CONFIG)
find_package(directxtk CONFIG REQUIRED)  # CommonLibSSE-NG links Microsoft::DirectXTK

add_commonlibsse_plugin(${PROJECT_NAME} SOURCES ${headers} ${sources})

# Build line: 1 (SE/AE 1.6, CommonLibSSE-NG 3.7) or 17 (Skyrim 1.7.x, CommonLibSSE-NG 7.2).
# The build-relwithdebinfo-17 preset sets this to 17; source #if-branches the NG 3.7 -> 7.2 API renames.
set(RUNTIME_LINE "1" CACHE STRING "Build line: 1 (SE/AE 1.6) or 17 (Skyrim 1.7.x)")
target_compile_definitions(${PROJECT_NAME} PRIVATE RUNTIME_LINE=${RUNTIME_LINE})
add_library("${PROJECT_NAME}::${PROJECT_NAME}" ALIAS "${PROJECT_NAME}")

# The DLL and PDB are named SimpleDodge (the target name). Another dodge DLL that hooks the same input
# must not be loaded beside it, or every dodge fires twice.
set_target_properties(${PROJECT_NAME} PROPERTIES OUTPUT_NAME "SimpleDodge")

if (MSVC)
	# Debug symbols (rule 43) and no build-machine paths in the DLL (rule 45).
	target_compile_options(${PROJECT_NAME} PRIVATE /Zi)
	target_link_options(${PROJECT_NAME} PRIVATE /DEBUG:FULL /OPT:REF /OPT:ICF)
	file(TO_NATIVE_PATH "${CMAKE_CURRENT_SOURCE_DIR}" PROJECT_NATIVE_DIR)
	target_compile_options(${PROJECT_NAME} PRIVATE "/d1trimfile:${PROJECT_NATIVE_DIR}")
	target_link_options(${PROJECT_NAME} PRIVATE /PDBALTPATH:%_PDB%)
endif()

target_include_directories(
	${PROJECT_NAME}
	PRIVATE
		${CMAKE_CURRENT_SOURCE_DIR}/include
		${CMAKE_CURRENT_SOURCE_DIR}/src
		${CMAKE_CURRENT_SOURCE_DIR}/extern/clib-util/include
)

target_link_libraries(
	${PROJECT_NAME}
	PRIVATE
		CommonLibSSE::CommonLibSSE
		spdlog::spdlog_header_only
)

target_precompile_headers(${PROJECT_NAME} PRIVATE include/PCH.h)

target_sources(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/version.rc)
