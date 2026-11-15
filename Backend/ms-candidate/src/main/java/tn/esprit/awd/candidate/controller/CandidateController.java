package tn.esprit.awd.candidate.controller;

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
import tn.esprit.awd.candidate.dto.CandidateRequest;
import tn.esprit.awd.candidate.dto.CandidateResponse;
import tn.esprit.awd.candidate.service.CandidateService;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/candidates")
public class CandidateController {

    private final CandidateService candidateService;

    public CandidateController(CandidateService candidateService) {
        this.candidateService = candidateService;
    }

    @GetMapping
    public List<CandidateResponse> findAll() {
        return candidateService.findAll();
    }

    @GetMapping("/{id}")
    public CandidateResponse findById(@PathVariable Long id) {
        return candidateService.findById(id);
    }

    @PostMapping
    public ResponseEntity<CandidateResponse> create(@Valid @RequestBody CandidateRequest request) {
        CandidateResponse created = candidateService.create(request);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}").buildAndExpand(created.id()).toUri();
        return ResponseEntity.created(location).body(created);
    }

    @PutMapping("/{id}")
    public CandidateResponse update(@PathVariable Long id, @Valid @RequestBody CandidateRequest request) {
        return candidateService.update(id, request);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        candidateService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @PutMapping("/{id}/address/{addressId}")
    public CandidateResponse assignAddress(@PathVariable Long id, @PathVariable Long addressId) {
        return candidateService.assignAddress(id, addressId);
    }

    @DeleteMapping("/{id}/address")
    public CandidateResponse removeAddress(@PathVariable Long id) {
        return candidateService.removeAddress(id);
    }
}
