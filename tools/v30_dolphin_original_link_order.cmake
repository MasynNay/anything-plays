# Original-source-preserving CMake-only fix for GNU ld static dependency order.
#
# Pinned upstream Dolphin 32c61f9: original common.a contains the symbols
# Common::DynamicLibrary. The original Dolphin Libretro video helper archive
# calls them. In the actual native build, the transitive archive order places
# common.a BEFORE a later videocontexts.a, so GNU ld rejects those calls.
#
# Crucially, adding --start-group via target_link_options() and --end-group
# via target_link_libraries() DOES NOT work: generated CMake places the end
# marker before the final common.a and videocontexts.a transitives. That
# exact failed real Linux build is recorded in CI run 42553003714.
#
# Use CMake LINK_GROUP RESCAN generator expression on the TWO cyclic original
# archive targets instead. The feature emits --start-group, common.a,
# videocontexts.a, --end-group together late in the actual linker command.
# Proven with native GNU ld/Ninja fixture on the same dependency topology.
# No original source file or library contents are modified.
function(_anything_plays_original_dolphin_link_group)
  if(NOT TARGET dolphin_libretro OR NOT TARGET dolphin_libretro_videocontexts
      OR NOT TARGET common)
    message(FATAL_ERROR "Original Dolphin source-linked native targets absent")
  endif()
  # An upstream target with the expected name but a different kind is not
  # the pinned original static archive. Refuse to attest a source build.
  foreach(_archive_target IN ITEMS common dolphin_libretro_videocontexts)
    get_target_property(_archive_type ${_archive_target} TYPE)
    if(NOT _archive_type STREQUAL "STATIC_LIBRARY")
      message(FATAL_ERROR "Original Dolphin archive target is not STATIC_LIBRARY: ${_archive_target}")
    endif()
  endforeach()
  if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "Original Dolphin GNU ld RESCAN source fix is Linux only")
  endif()
  target_link_libraries(dolphin_libretro PRIVATE
    "$<LINK_GROUP:RESCAN,common,dolphin_libretro_videocontexts>")
  message(STATUS "Original Dolphin source preserved: GNU RESCAN common/videocontexts group")
endfunction()
cmake_language(DEFER CALL _anything_plays_original_dolphin_link_group)
