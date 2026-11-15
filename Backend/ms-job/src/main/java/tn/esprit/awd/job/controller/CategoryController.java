package tn.esprit.awd.job.controller;

import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;
import tn.esprit.awd.job.dto.CategoryRequest;
import tn.esprit.awd.job.dto.CategoryResponse;
import tn.esprit.awd.job.dto.JobResponse;
import tn.esprit.awd.job.service.CategoryService;
import tn.esprit.awd.job.service.JobService;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/categories")
public class CategoryController {

    private final CategoryService categoryService;
    private final JobService jobService;

    public CategoryController(CategoryService categoryService, JobService jobService) {
        this.categoryService = categoryService;
        this.jobService = jobService;
    }

    @GetMapping
    public List<CategoryResponse> findAll() {
        return categoryService.findAll();
    }

    @GetMapping("/{id}")
    public CategoryResponse findById(@PathVariable Long id) {
        return categoryService.findById(id);
    }

    @GetMapping("/{id}/jobs")
    public List<JobResponse> findJobs(@PathVariable Long id) {
        return jobService.search(null, id);
    }

    @PostMapping
    public ResponseEntity<CategoryResponse> create(@Valid @RequestBody CategoryRequest request) {
        CategoryResponse created = categoryService.create(request);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}").buildAndExpand(created.id()).toUri();
        return ResponseEntity.created(location).body(created);
    }

    @PutMapping("/{id}")
    public CategoryResponse update(@PathVariable Long id, @Valid @RequestBody CategoryRequest request) {
        return categoryService.update(id, request);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        categoryService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
